/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include "esn_classifier_weights.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */



UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */
#define N 500
#define ESN_FIXED_POINT 0 // Set to 1 to enable Q15 Fixed-Point ESN Inference

// Reservoir states
float esn_x[ESN_N_RESERVOIR] = {0.0f};
int16_t esn_x_q[ESN_N_RESERVOIR] = {0};

// Helper function to scale float to Q15
int16_t float_to_q15(float v) {
    float temp = v * 32768.0f;
    if (temp >= 32767.0f) return 32767;
    if (temp <= -32768.0f) return -32768;
    return (int16_t)temp;
}

// Helper function to scale float to Q12
int16_t float_to_q12(float v) {
    float temp = v * 4096.0f;
    if (temp >= 32767.0f) return 32767;
    if (temp <= -32768.0f) return -32768;
    return (int16_t)temp;
}

// Pre-quantized arrays for high-performance fixed-point execution
int16_t tanh_lut[33];
int16_t esn_W_in_q15[ESN_N_RESERVOIR][1 + ESN_N_INPUTS];
int16_t esn_W_res_val_q15[ESN_W_RES_NNZ];

// Initialise lookup table for high-speed integer activation (covers 0.0 to 8.0 in steps of 0.25)
void init_tanh_lut(void) {
    for (int i = 0; i <= 32; i++) {
        float x = (float)i * 0.25f;
        float y = tanhf(x);
        tanh_lut[i] = float_to_q15(y);
    }
}

// Initialise weights into Q15 format at startup to avoid runtime float ops
void init_fixed_point_weights(void) {
    for (int i = 0; i < ESN_N_RESERVOIR; i++) {
        for (int j = 0; j < 1 + ESN_N_INPUTS; j++) {
            esn_W_in_q15[i][j] = float_to_q15(esn_W_in[i][j]);
        }
    }
    for (int i = 0; i < ESN_W_RES_NNZ; i++) {
        esn_W_res_val_q15[i] = float_to_q15(esn_W_res_val[i]);
    }
}

// Tanh function in Q15 precision using LUT linear interpolation (no floats, safe against overflow)
int16_t q15_tanh(int16_t x_q15) {
    if (x_q15 == -32768) x_q15 = -32767;
    int16_t abs_x = x_q15 < 0 ? -x_q15 : x_q15;
    int idx = abs_x >> 10; // 0 to 31
    int frac = abs_x & 1023;
    int32_t y = ((1024 - frac) * (int32_t)tanh_lut[idx] + frac * (int32_t)tanh_lut[idx + 1]) >> 10;
    return x_q15 < 0 ? -((int16_t)y) : (int16_t)y;
}

// Perform ESN prediction step in float32 (with CSR optimization)
void esn_predict_float(const float u[ESN_N_INPUTS], float y_pred[ESN_N_OUTPUTS]) {
    // 1. Scale inputs using means and standard deviations
    float u_scaled[ESN_N_INPUTS];
    for (int i = 0; i < ESN_N_INPUTS; i++) {
        u_scaled[i] = (u[i] - esn_input_means[i]) / esn_input_stds[i];
    }

    // 2. Update reservoir states using CSR Sparse Matrix Multiplication
    float arg[ESN_N_RESERVOIR];
    for (int i = 0; i < ESN_N_RESERVOIR; i++) {
        // Bias + input multiplication
        float sum = esn_W_in[i][0] * 1.0f; // Bias input is 1.0f
        for (int j = 0; j < ESN_N_INPUTS; j++) {
            sum += esn_W_in[i][1 + j] * u_scaled[j];
        }

        // Sparse reservoir matrix multiplication (SpMV via CSR)
        uint16_t start = esn_W_res_row_ptr[i];
        uint16_t end = esn_W_res_row_ptr[i + 1];
        for (uint16_t k = start; k < end; k++) {
            uint16_t col_idx = esn_W_res_col[k];
            sum += esn_W_res_val[k] * esn_x[col_idx];
        }
        arg[i] = sum;
    }

    // 3. Apply leak rate and tanh activation
    for (int i = 0; i < ESN_N_RESERVOIR; i++) {
        esn_x[i] = (1.0f - ESN_LEAK_RATE) * esn_x[i] + ESN_LEAK_RATE * tanhf(arg[i]);
    }

    // 4. Compute output: y_pred = W_out * [1.0, u_scaled, esn_x]
    for (int i = 0; i < ESN_N_OUTPUTS; i++) {
        float sum = esn_W_out[i][0] * 1.0f; // Bias
        for (int j = 0; j < ESN_N_INPUTS; j++) {
            sum += esn_W_out[i][1 + j] * u_scaled[j];
        }
        for (int j = 0; j < ESN_N_RESERVOIR; j++) {
            sum += esn_W_out[i][1 + ESN_N_INPUTS + j] * esn_x[j];
        }
        y_pred[i] = sum;
    }
}

// Perform ESN prediction step in Q15 fixed-point (with CSR optimization, pure integer path)
void esn_predict_fixed(const float u[ESN_N_INPUTS], float y_pred[ESN_N_OUTPUTS]) {
    // 1. Scale inputs and convert to Q12 format (range +/- 8.0)
    int16_t u_scaled_q12[ESN_N_INPUTS];
    for (int i = 0; i < ESN_N_INPUTS; i++) {
        float val = (u[i] - esn_input_means[i]) / esn_input_stds[i];
        u_scaled_q12[i] = float_to_q12(val);
    }

    // 2. Update reservoir states using CSR (sum calculated in Q12 format to allow arg range up to +/- 8.0)
    int16_t arg_q12[ESN_N_RESERVOIR];
    for (int i = 0; i < ESN_N_RESERVOIR; i++) {
        // Bias term: W_in_q15[i][0] is in Q15. Bias input is 1.0.
        // (Q15 * 1.0) in Q12 is (W_in_q15[i][0] * 4096) >> 15 = W_in_q15[i][0] >> 3
        int32_t sum = ((int32_t)esn_W_in_q15[i][0]) >> 3;

        // Input terms: W_in_q15[i][1+j] is in Q15, u_scaled_q12 is in Q12
        // (Q15 * Q12) >> 15 = Q12
        for (int j = 0; j < ESN_N_INPUTS; j++) {
            sum += ((int32_t)esn_W_in_q15[i][1 + j] * u_scaled_q12[j]) >> 15;
        }

        // Reservoir terms: W_res is in Q15, esn_x_q is in Q15
        // (Q15 * Q15) >> 18 = Q12
        uint16_t start = esn_W_res_row_ptr[i];
        uint16_t end = esn_W_res_row_ptr[i + 1];
        for (uint16_t k = start; k < end; k++) {
            uint16_t col_idx = esn_W_res_col[k];
            sum += ((int32_t)esn_W_res_val_q15[k] * esn_x_q[col_idx]) >> 18;
        }
        
        // Clip to avoid overflow of 16-bit signed integer (Q12 limit +/- 8.0)
        if (sum > 32767) sum = 32767;
        if (sum < -32768) sum = -32768;
        arg_q12[i] = (int16_t)sum;
    }

    // 3. Apply leak rate and tanh activation:
    // x_q(t) = (1 - alpha) * x_q(t-1) + alpha * tanh(arg_q12)
    // ESN_LEAK_RATE is 0.3f, which in Q15 is 9830.
    // 1 - ESN_LEAK_RATE is 0.7f, which in Q15 is 22938.
    int16_t leak_rate_q15 = 9830;
    int16_t one_minus_leak_rate_q15 = 22938;

    for (int i = 0; i < ESN_N_RESERVOIR; i++) {
        // arg_q12[i] is in Q12, which represents up to 8.0, and q15_tanh expects Q12 input!
        int16_t tanh_val = q15_tanh(arg_q12[i]);
        int32_t state_update = ((int32_t)one_minus_leak_rate_q15 * esn_x_q[i]) >> 15;
        state_update += ((int32_t)leak_rate_q15 * tanh_val) >> 15;
        
        if (state_update > 32767) state_update = 32767;
        if (state_update < -32768) state_update = -32768;
        esn_x_q[i] = (int16_t)state_update;
    }

    // 4. Compute output: y_pred = W_out * [1.0, u_scaled, esn_x_q] (Readout in float)
    for (int i = 0; i < ESN_N_OUTPUTS; i++) {
        float sum = esn_W_out[i][0] * 1.0f; // Bias
        for (int j = 0; j < ESN_N_INPUTS; j++) {
            float val = (u[j] - esn_input_means[j]) / esn_input_stds[j];
            sum += esn_W_out[i][1 + j] * val;
        }
        for (int j = 0; j < ESN_N_RESERVOIR; j++) {
            float state_f = (float)esn_x_q[j] / 32768.0f;
            sum += esn_W_out[i][1 + ESN_N_INPUTS + j] * state_f;
        }
        y_pred[i] = sum;
    }
}

float data[500][4] = {
  {11.685, 2.388, 32.538, 0},
  {11.457, 2.311, 32.541, 0},
  {11.589, 2.420, 32.544, 0},
  {11.649, 2.377, 32.547, 0},
  {11.418, 2.367, 32.550, 0},
  {11.571, 2.448, 32.553, 0},
  {11.432, 2.410, 32.555, 0},
  {11.475, 2.461, 32.558, 0},
  {11.456, 2.441, 32.561, 0},
  {11.473, 2.347, 32.563, 0},
  {11.492, 2.361, 32.566, 0},
  {11.439, 2.436, 32.568, 0},
  {11.460, 2.353, 32.571, 0},
  {11.573, 2.370, 32.573, 0},
  {11.690, 2.351, 32.576, 0},
  {11.369, 2.395, 32.578, 0},
  {11.496, 2.429, 32.580, 0},
  {11.557, 2.345, 32.583, 0},
  {11.571, 2.352, 32.585, 0},
  {11.617, 2.426, 32.588, 0},
  {11.535, 2.465, 32.590, 0},
  {11.347, 2.429, 32.593, 0},
  {11.588, 2.315, 32.595, 0},
  {11.610, 2.383, 32.598, 0},
  {11.465, 2.404, 32.600, 0},
  {11.488, 2.395, 32.603, 0},
  {11.461, 2.368, 32.605, 0},
  {11.502, 2.311, 32.608, 0},
  {11.424, 2.463, 32.611, 0},
  {11.635, 2.460, 32.614, 0},
  {11.394, 2.447, 32.617, 0},
  {11.477, 2.397, 32.620, 0},
  {11.646, 2.355, 32.623, 0},
  {11.551, 2.456, 32.626, 0},
  {11.475, 2.390, 32.629, 0},
  {11.467, 2.427, 32.633, 0},
  {11.547, 2.509, 32.636, 0},
  {11.597, 2.502, 32.640, 0},
  {11.577, 2.445, 32.644, 0},
  {11.677, 2.488, 32.648, 0},
  {11.401, 2.445, 32.652, 0},
  {11.482, 2.449, 32.657, 0},
  {11.296, 2.488, 32.661, 0},
  {11.537, 2.444, 32.666, 0},
  {11.567, 2.613, 32.671, 0},
  {11.500, 2.555, 32.677, 0},
  {11.321, 2.504, 32.682, 0},
  {11.281, 2.554, 32.688, 0},
  {11.666, 2.616, 32.694, 0},
  {11.357, 2.573, 32.700, 0},
  {11.572, 2.585, 32.707, 0},
  {11.458, 2.650, 32.714, 0},
  {11.465, 2.701, 32.721, 0},
  {11.408, 2.687, 32.729, 0},
  {11.523, 2.667, 32.737, 0},
  {11.447, 2.704, 32.746, 0},
  {11.352, 2.697, 32.755, 0},
  {11.424, 2.693, 32.764, 0},
  {11.449, 2.702, 32.774, 0},
  {11.433, 2.717, 32.784, 0},
  {11.487, 2.735, 32.795, 0},
  {11.478, 2.800, 32.806, 0},
  {11.182, 2.743, 32.818, 0},
  {11.350, 2.839, 32.830, 0},
  {11.412, 2.795, 32.843, 0},
  {11.466, 2.882, 32.856, 0},
  {11.482, 2.875, 32.871, 0},
  {11.462, 2.955, 32.885, 0},
  {11.365, 3.024, 32.901, 0},
  {11.541, 2.920, 32.917, 0},
  {11.310, 2.996, 32.934, 0},
  {11.238, 3.025, 32.951, 0},
  {11.422, 3.071, 32.970, 0},
  {11.469, 3.115, 32.989, 0},
  {11.464, 3.111, 33.009, 0},
  {11.412, 3.177, 33.029, 0},
  {11.441, 3.274, 33.051, 0},
  {11.362, 3.266, 33.074, 0},
  {11.496, 3.269, 33.097, 0},
  {11.467, 3.345, 33.122, 0},
  {11.334, 3.393, 33.147, 0},
  {11.396, 3.315, 33.174, 0},
  {11.421, 3.433, 33.201, 0},
  {11.452, 3.579, 33.230, 0},
  {11.281, 3.522, 33.259, 0},
  {11.412, 3.568, 33.290, 0},
  {11.388, 3.678, 33.322, 0},
  {11.368, 3.580, 33.355, 0},
  {11.382, 3.724, 33.389, 0},
  {11.243, 3.708, 33.424, 0},
  {11.307, 3.778, 33.461, 0},
  {11.345, 3.839, 33.499, 0},
  {11.184, 3.841, 33.538, 0},
  {11.091, 3.863, 33.579, 0},
  {11.276, 3.971, 33.620, 0},
  {11.222, 3.977, 33.664, 0},
  {11.238, 4.033, 33.708, 0},
  {11.182, 4.102, 33.754, 0},
  {11.090, 4.161, 33.801, 0},
  {11.214, 4.149, 33.850, 0},
  {11.250, 4.157, 33.900, 0},
  {11.177, 4.272, 33.951, 0},
  {11.117, 4.362, 34.004, 0},
  {11.126, 4.310, 34.058, 0},
  {11.098, 4.411, 34.113, 0},
  {10.974, 4.501, 34.170, 0},
  {11.129, 4.471, 34.229, 0},
  {11.200, 4.536, 34.289, 0},
  {11.091, 4.558, 34.350, 0},
  {11.020, 4.561, 34.413, 0},
  {11.134, 4.611, 34.477, 0},
  {11.180, 4.633, 34.542, 0},
  {11.096, 4.729, 34.609, 0},
  {11.091, 4.870, 34.677, 0},
  {11.056, 4.834, 34.747, 0},
  {10.968, 4.945, 34.817, 0},
  {11.030, 4.860, 34.889, 0},
  {11.121, 4.921, 34.963, 0},
  {10.995, 5.073, 35.038, 1},
  {11.063, 4.958, 35.113, 1},
  {10.979, 4.999, 35.191, 1},
  {11.036, 5.203, 35.269, 1},
  {10.907, 5.190, 35.348, 1},
  {10.843, 5.190, 35.429, 1},
  {10.711, 5.218, 35.511, 1},
  {11.021, 5.307, 35.593, 1},
  {10.975, 5.319, 35.677, 1},
  {11.006, 5.358, 35.762, 1},
  {10.984, 5.426, 35.848, 1},
  {10.742, 5.452, 35.934, 1},
  {10.924, 5.432, 36.022, 1},
  {11.100, 5.385, 36.110, 1},
  {10.994, 5.552, 36.200, 1},
  {10.879, 5.464, 36.290, 1},
  {10.842, 5.419, 36.380, 1},
  {10.846, 5.592, 36.472, 1},
  {10.903, 5.609, 36.564, 1},
  {10.890, 5.599, 36.657, 1},
  {10.777, 5.663, 36.750, 1},
  {10.815, 5.751, 36.844, 1},
  {10.827, 5.725, 36.938, 1},
  {10.960, 5.718, 37.033, 1},
  {10.948, 5.762, 37.129, 1},
  {10.871, 5.698, 37.225, 1},
  {10.710, 5.729, 37.321, 1},
  {10.856, 5.772, 37.417, 1},
  {10.906, 5.790, 37.514, 1},
  {10.804, 5.979, 37.611, 1},
  {10.688, 5.918, 37.708, 1},
  {10.739, 5.959, 37.806, 1},
  {10.889, 5.914, 37.904, 1},
  {10.801, 5.911, 38.001, 1},
  {10.842, 6.005, 38.099, 1},
  {10.831, 6.004, 38.197, 1},
  {10.872, 5.979, 38.295, 1},
  {10.889, 5.927, 38.393, 1},
  {10.834, 6.138, 38.491, 1},
  {10.842, 6.150, 38.590, 1},
  {10.821, 6.010, 38.687, 1},
  {10.667, 6.141, 38.785, 1},
  {10.871, 6.078, 38.883, 1},
  {10.880, 6.076, 38.981, 1},
  {10.806, 6.068, 39.078, 1},
  {10.746, 6.110, 39.176, 1},
  {10.711, 6.154, 39.273, 1},
  {10.609, 6.087, 39.370, 1},
  {10.766, 6.176, 39.466, 1},
  {10.821, 6.105, 39.563, 1},
  {10.854, 6.184, 39.659, 1},
  {10.743, 6.156, 39.755, 1},
  {10.705, 6.277, 39.850, 1},
  {10.924, 6.189, 39.945, 1},
  {10.921, 6.223, 40.040, 1},
  {10.987, 6.266, 40.135, 1},
  {10.652, 6.243, 40.229, 1},
  {10.615, 6.234, 40.323, 1},
  {10.758, 6.183, 40.416, 1},
  {10.779, 6.261, 40.509, 1},
  {10.807, 6.346, 40.602, 1},
  {10.688, 6.318, 40.694, 1},
  {10.715, 6.247, 40.786, 1},
  {10.703, 6.361, 40.878, 1},
  {10.535, 6.314, 40.969, 1},
  {10.649, 6.365, 41.059, 1},
  {10.736, 6.343, 41.149, 1},
  {10.686, 6.226, 41.239, 1},
  {10.811, 6.296, 41.328, 1},
  {10.784, 6.436, 41.417, 1},
  {10.754, 6.353, 41.505, 1},
  {10.784, 6.339, 41.593, 1},
  {10.927, 6.389, 41.680, 1},
  {10.695, 6.411, 41.767, 1},
  {10.985, 6.352, 41.853, 1},
  {10.903, 6.410, 41.939, 1},
  {10.843, 6.337, 42.025, 1},
  {10.518, 6.372, 42.110, 1},
  {10.657, 6.381, 42.194, 1},
  {10.581, 6.427, 42.278, 1},
  {10.732, 6.519, 42.362, 1},
  {10.604, 6.459, 42.445, 1},
  {10.665, 6.389, 42.527, 1},
  {10.856, 6.356, 42.610, 1},
  {10.584, 6.406, 42.691, 1},
  {10.521, 6.525, 42.772, 1},
  {10.630, 6.482, 42.853, 1},
  {10.678, 6.407, 42.933, 1},
  {10.771, 6.533, 43.013, 1},
  {10.714, 6.429, 43.092, 1},
  {10.665, 6.475, 43.171, 1},
  {10.723, 6.447, 43.249, 1},
  {10.585, 6.486, 43.327, 1},
  {10.728, 6.458, 43.405, 1},
  {10.800, 6.460, 43.482, 1},
  {10.694, 6.465, 43.558, 1},
  {10.813, 6.609, 43.635, 1},
  {10.660, 6.412, 43.710, 1},
  {10.795, 6.568, 43.786, 1},
  {10.557, 6.499, 43.860, 1},
  {10.695, 6.555, 43.935, 1},
  {10.747, 6.584, 44.009, 1},
  {10.584, 6.464, 44.082, 1},
  {10.540, 6.579, 44.156, 1},
  {10.627, 6.534, 44.228, 1},
  {10.660, 6.500, 44.301, 1},
  {10.820, 6.555, 44.373, 1},
  {10.583, 6.557, 44.444, 1},
  {10.787, 6.582, 44.516, 1},
  {10.656, 6.592, 44.586, 1},
  {10.618, 6.562, 44.657, 1},
  {10.644, 6.620, 44.727, 1},
  {10.892, 6.603, 44.797, 1},
  {10.616, 6.656, 44.866, 1},
  {10.828, 6.669, 44.935, 1},
  {10.684, 6.578, 45.004, 2},
  {10.624, 6.594, 45.072, 2},
  {10.744, 6.666, 45.140, 2},
  {10.684, 6.720, 45.208, 2},
  {10.662, 6.688, 45.275, 2},
  {10.718, 6.629, 45.342, 2},
  {10.621, 6.644, 45.409, 2},
  {10.880, 6.720, 45.475, 2},
  {10.677, 6.588, 45.541, 2},
  {10.746, 6.638, 45.607, 2},
  {10.766, 6.616, 45.672, 2},
  {10.570, 6.731, 45.737, 2},
  {10.810, 6.604, 45.802, 2},
  {10.760, 6.645, 45.867, 2},
  {10.586, 6.680, 45.931, 2},
  {10.691, 6.699, 45.995, 2},
  {10.567, 6.668, 46.059, 2},
  {10.780, 6.643, 46.122, 2},
  {10.653, 6.683, 46.186, 2},
  {10.746, 6.689, 46.249, 2},
  {10.659, 6.651, 46.311, 2},
  {10.679, 6.649, 46.374, 2},
  {10.602, 6.732, 46.436, 2},
  {10.604, 6.762, 46.498, 2},
  {10.630, 6.760, 46.560, 2},
  {10.890, 6.739, 46.622, 2},
  {10.734, 6.713, 46.683, 2},
  {10.702, 6.668, 46.744, 2},
  {10.699, 6.706, 46.805, 2},
  {10.883, 6.731, 46.866, 2},
  {10.688, 6.753, 46.926, 2},
  {10.706, 6.786, 46.987, 2},
  {10.578, 6.791, 47.047, 2},
  {10.636, 6.827, 47.107, 2},
  {10.533, 6.809, 47.166, 2},
  {10.690, 6.728, 47.226, 2},
  {10.568, 6.843, 47.285, 2},
  {10.770, 6.756, 47.344, 2},
  {10.730, 6.792, 47.404, 2},
  {10.624, 6.785, 47.462, 2},
  {10.594, 6.859, 47.521, 2},
  {10.491, 6.745, 47.580, 2},
  {10.712, 6.869, 47.638, 2},
  {10.712, 6.808, 47.696, 2},
  {10.615, 6.808, 47.754, 2},
  {10.834, 6.791, 47.812, 2},
  {10.682, 6.822, 47.870, 2},
  {10.681, 6.808, 47.928, 2},
  {10.622, 6.830, 47.985, 2},
  {10.695, 6.941, 48.042, 2},
  {10.543, 6.878, 48.100, 2},
  {10.606, 6.841, 48.157, 2},
  {10.515, 6.959, 48.214, 2},
  {10.490, 6.937, 48.271, 2},
  {10.428, 6.932, 48.327, 2},
  {10.770, 6.892, 48.384, 2},
  {10.406, 6.959, 48.440, 2},
  {10.844, 6.900, 48.497, 2},
  {10.684, 6.899, 48.553, 2},
  {10.394, 6.914, 48.609, 2},
  {10.596, 6.928, 48.665, 2},
  {10.692, 6.984, 48.721, 2},
  {10.533, 7.009, 48.777, 2},
  {10.680, 6.870, 48.833, 2},
  {10.496, 6.953, 48.888, 2},
  {10.608, 6.910, 48.944, 2},
  {10.749, 7.049, 48.999, 2},
  {10.633, 7.076, 49.055, 2},
  {10.718, 6.969, 49.110, 2},
  {10.600, 7.051, 49.165, 2},
  {10.524, 7.042, 49.220, 2},
  {10.642, 7.040, 49.275, 2},
  {10.595, 7.073, 49.330, 2},
  {10.801, 7.071, 49.385, 2},
  {10.505, 7.052, 49.440, 2},
  {10.595, 7.010, 49.494, 2},
  {10.438, 7.128, 49.549, 2},
  {10.746, 7.009, 49.604, 2},
  {10.648, 7.061, 49.658, 2},
  {10.722, 7.054, 49.712, 2},
  {10.554, 7.128, 49.767, 2},
  {10.623, 7.144, 49.821, 2},
  {10.707, 7.155, 49.875, 2},
  {10.546, 7.167, 49.929, 2},
  {10.631, 7.032, 49.983, 2},
  {10.433, 7.127, 50.037, 2},
  {10.543, 7.116, 50.091, 2},
  {10.559, 7.090, 50.145, 2},
  {10.499, 7.136, 50.199, 2},
  {10.411, 7.118, 50.252, 2},
  {10.596, 7.077, 50.306, 2},
  {10.590, 7.105, 50.360, 2},
  {10.627, 7.103, 50.413, 2},
  {10.660, 7.112, 50.467, 2},
  {10.475, 7.156, 50.520, 2},
  {10.587, 7.179, 50.573, 2},
  {10.574, 7.125, 50.627, 2},
  {10.679, 7.103, 50.680, 2},
  {10.650, 7.133, 50.733, 2},
  {10.478, 7.222, 50.786, 2},
  {10.374, 7.240, 50.839, 2},
  {10.473, 7.132, 50.892, 2},
  {10.652, 7.226, 50.945, 2},
  {10.551, 7.191, 50.998, 2},
  {10.531, 7.173, 51.051, 2},
  {10.480, 7.239, 51.104, 2},
  {10.486, 7.161, 51.157, 2},
  {10.594, 7.166, 51.209, 2},
  {10.622, 7.222, 51.262, 2},
  {10.596, 7.130, 51.314, 2},
  {10.562, 7.210, 51.367, 2},
  {10.660, 7.189, 51.420, 2},
  {10.524, 7.172, 51.472, 2},
  {10.540, 7.222, 51.524, 2},
  {10.442, 7.273, 51.577, 2},
  {10.559, 7.260, 51.629, 2},
  {10.524, 7.391, 51.681, 2},
  {10.435, 7.277, 51.733, 2},
  {10.592, 7.246, 51.786, 2},
  {10.562, 7.331, 51.838, 2},
  {10.741, 7.331, 51.890, 2},
  {10.585, 7.257, 51.942, 2},
  {10.584, 7.303, 51.994, 2},
  {10.514, 7.255, 52.046, 2},
  {10.422, 7.299, 52.098, 2},
  {10.411, 7.306, 52.150, 2},
  {10.563, 7.432, 52.201, 2},
  {10.682, 7.365, 52.253, 2},
  {10.565, 7.276, 52.305, 2},
  {10.622, 7.267, 52.356, 2},
  {10.477, 7.307, 52.408, 2},
  {10.556, 7.364, 52.460, 2},
  {10.498, 7.444, 52.511, 2},
  {10.444, 7.323, 52.563, 2},
  {10.597, 7.349, 52.614, 2},
  {10.494, 7.282, 52.665, 2},
  {10.200, 7.425, 52.717, 2},
  {10.714, 7.398, 52.768, 2},
  {10.490, 7.416, 52.819, 2},
  {10.558, 7.412, 52.870, 2},
  {10.473, 7.274, 52.921, 2},
  {10.534, 7.437, 52.972, 2},
  {10.491, 7.381, 53.023, 2},
  {10.511, 7.356, 53.074, 2},
  {10.473, 7.367, 53.125, 2},
  {10.405, 7.447, 53.176, 2},
  {10.469, 7.490, 53.227, 2},
  {10.544, 7.448, 53.277, 2},
  {10.495, 7.490, 53.328, 2},
  {10.674, 7.375, 53.378, 2},
  {10.823, 7.328, 53.429, 2},
  {10.437, 7.387, 53.479, 2},
  {10.425, 7.354, 53.529, 2},
  {10.407, 7.354, 53.580, 2},
  {10.414, 7.393, 53.630, 2},
  {10.500, 7.338, 53.680, 2},
  {10.546, 7.369, 53.730, 2},
  {10.526, 7.410, 53.779, 2},
  {10.380, 7.423, 53.829, 2},
  {10.663, 7.378, 53.878, 2},
  {10.606, 7.406, 53.928, 2},
  {10.411, 7.418, 53.977, 2},
  {10.486, 7.402, 54.026, 2},
  {10.461, 7.456, 54.075, 2},
  {10.504, 7.376, 54.124, 2},
  {10.446, 7.444, 54.172, 2},
  {10.438, 7.497, 54.221, 2},
  {10.528, 7.505, 54.269, 2},
  {10.479, 7.395, 54.317, 2},
  {10.510, 7.446, 54.364, 2},
  {10.475, 7.371, 54.412, 2},
  {10.496, 7.443, 54.459, 2},
  {10.532, 7.335, 54.506, 2},
  {10.445, 7.331, 54.553, 2},
  {10.649, 7.370, 54.600, 2},
  {10.571, 7.323, 54.646, 2},
  {10.236, 7.438, 54.692, 2},
  {10.445, 7.415, 54.738, 2},
  {10.576, 7.459, 54.783, 2},
  {10.606, 7.422, 54.828, 2},
  {10.370, 7.437, 54.873, 2},
  {10.690, 7.353, 54.917, 2},
  {10.510, 7.443, 54.961, 2},
  {10.364, 7.395, 55.005, 2},
  {10.473, 7.360, 55.048, 2},
  {10.451, 7.446, 55.090, 2},
  {10.674, 7.423, 55.133, 2},
  {10.298, 7.372, 55.175, 2},
  {10.438, 7.391, 55.216, 2},
  {10.558, 7.354, 55.257, 2},
  {10.594, 7.326, 55.297, 2},
  {10.359, 7.373, 55.337, 2},
  {10.659, 7.344, 55.376, 2},
  {10.382, 7.333, 55.415, 2},
  {10.436, 7.364, 55.453, 2},
  {10.491, 7.316, 55.490, 2},
  {10.611, 7.317, 55.527, 2},
  {10.583, 7.410, 55.563, 2},
  {10.530, 7.206, 55.599, 2},
  {10.619, 7.274, 55.634, 2},
  {10.478, 7.241, 55.668, 2},
  {10.691, 7.399, 55.701, 2},
  {10.545, 7.276, 55.734, 2},
  {10.353, 7.362, 55.766, 2},
  {10.449, 7.280, 55.797, 2},
  {10.443, 7.265, 55.827, 2},
  {10.430, 7.193, 55.857, 2},
  {10.611, 7.188, 55.885, 2},
  {10.426, 7.228, 55.913, 2},
  {10.549, 7.189, 55.940, 2},
  {10.539, 7.312, 55.966, 2},
  {10.477, 7.140, 55.991, 2},
  {10.567, 7.255, 56.015, 2},
  {10.488, 7.194, 56.038, 2},
  {10.746, 7.142, 56.060, 2},
  {10.413, 7.094, 56.080, 2},
  {10.593, 7.095, 56.100, 2},
  {10.520, 7.084, 56.119, 2},
  {10.552, 7.036, 56.137, 2},
  {10.403, 7.164, 56.153, 2},
  {10.663, 7.031, 56.169, 2},
  {10.604, 6.995, 56.183, 2},
  {10.695, 7.040, 56.196, 2},
  {10.651, 7.023, 56.207, 2},
  {10.513, 6.935, 56.218, 2},
  {10.474, 6.963, 56.227, 2},
  {10.548, 6.980, 56.235, 2},
  {10.655, 7.013, 56.241, 2},
  {10.497, 6.911, 56.247, 2},
  {10.587, 6.955, 56.250, 2},
  {10.397, 6.807, 56.253, 2},
  {10.521, 6.846, 56.254, 2},
  {10.671, 6.853, 56.254, 2},
  {10.710, 6.701, 56.252, 2},
  {10.772, 6.811, 56.249, 2},
  {10.680, 6.745, 56.244, 2},
  {10.678, 6.697, 56.238, 2},
  {10.549, 6.787, 56.230, 2},
  {10.454, 6.717, 56.220, 2},
  {10.757, 6.640, 56.210, 2},
  {10.716, 6.633, 56.197, 2},
  {10.712, 6.553, 56.183, 2},
  {10.739, 6.545, 56.168, 2},
  {10.635, 6.638, 56.150, 2},
  {10.796, 6.642, 56.131, 2},
  {10.786, 6.552, 56.111, 2},
  {10.667, 6.448, 56.089, 2},
  {10.640, 6.472, 56.065, 2},
  {10.702, 6.398, 56.040, 2},
  {10.780, 6.360, 56.013, 2},
  {10.835, 6.414, 55.984, 2},
  {10.825, 6.433, 55.954, 2},
  {10.543, 6.315, 55.922, 2},
  {10.768, 6.319, 55.888, 2},
  {10.438, 6.202, 55.853, 2},
  {10.592, 6.191, 55.816, 2},
  {10.673, 6.155, 55.778, 2},
  {10.769, 6.205, 55.737, 2},
  {10.766, 6.082, 55.696, 2},
  {10.766, 6.072, 55.652, 2},
  {10.889, 6.067, 55.607, 2},
  {10.803, 5.981, 55.561, 2},
  {10.887, 5.922, 55.512, 2},
  {10.798, 5.923, 55.463, 2},
  {10.721, 5.863, 55.411, 2},
  {10.701, 5.837, 55.359, 2},
  {10.946, 5.873, 55.304, 2},
};



/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MPU_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART2_UART_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

#include <stdio.h>

#ifndef HOST_SIMULATION
int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart2, (uint8_t *)&ch, 1, HAL_MAX_DELAY);
    return ch;
}
#endif
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MPU Configuration--------------------------------------------------------*/
  MPU_Config();

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART2_UART_Init();
  /* USER CODE BEGIN 2 */
  init_tanh_lut();
  init_fixed_point_weights();
  printf("System Started\r\n");
  /* USER CODE END 2 */



  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
      int correct_predictions = 0;

      // Reset ESN states at the start of loop
      #if ESN_FIXED_POINT
      for(int i = 0; i < ESN_N_RESERVOIR; i++) esn_x_q[i] = 0;
      #else
      for(int i = 0; i < ESN_N_RESERVOIR; i++) esn_x[i] = 0.0f;
      #endif

      printf("\r\n--- Starting ESN Inference Loop (N=%d) ---\r\n", N);

      for(int k = 0; k < N; k++)
      {
          float V = data[k][0];
          float I = data[k][1];
          float T = data[k][2];
          int true_state = (int)data[k][3];

          float u[ESN_N_INPUTS] = {V, I, T};
          float y_pred[ESN_N_OUTPUTS] = {0.0f};

          // -------- Reservoir Computing Inference --------
          #if ESN_FIXED_POINT
          esn_predict_fixed(u, y_pred);
          #else
          esn_predict_float(u, y_pred);
          #endif

          // Argmax readout classification
          int predicted_state = 0;
          float max_val = y_pred[0];
          for (int i = 1; i < ESN_N_OUTPUTS; i++) {
              if (y_pred[i] > max_val) {
                  max_val = y_pred[i];
                  predicted_state = i;
              }
          }

          if (predicted_state == true_state) {
              correct_predictions++;
          }

          // -------- Output and Control --------
          const char* label_str[] = {"NORMAL  ", "WARNING ", "CRITICAL"};
          printf("[%3d] True=%s Pred=%s | V=%d I=%d T=%d\r\n", 
                 k, label_str[true_state], label_str[predicted_state], 
                 (int)V, (int)I, (int)T);

          switch(predicted_state)
          {
              case 0:
                  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);
                  break;

              case 1:
                  HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
                  break;

              case 2:
                  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);
                  break;
          }

          HAL_Delay(50); // Fast delay for simulation
      }

      float accuracy = ((float)correct_predictions / N) * 100.0f;
      printf("--- Loop Complete. Accuracy: %.2f%% ---\r\n\r\n", accuracy);
      #ifdef HOST_SIMULATION
      break; // Exit the loop in host simulation
      #else
      HAL_Delay(5000);
      #endif
      /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
#ifndef HOST_SIMULATION
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Supply configuration update enable
  */
  HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

  /** Configure the main internal regulator output voltage
  */
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE2);

  while(!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_DIV1;
  RCC_OscInitStruct.HSICalibrationValue = 64;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 4;
  RCC_OscInitStruct.PLL.PLLN = 12;
  RCC_OscInitStruct.PLL.PLLP = 1;
  RCC_OscInitStruct.PLL.PLLQ = 4;
  RCC_OscInitStruct.PLL.PLLR = 2;
  RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_3;
  RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
  RCC_OscInitStruct.PLL.PLLFRACN = 0;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2
                              |RCC_CLOCKTYPE_D3PCLK1|RCC_CLOCKTYPE_D1PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
  RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    Error_Handler();
  }
#endif
}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{
#ifndef HOST_SIMULATION
  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  huart2.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart2.Init.ClockPrescaler = UART_PRESCALER_DIV1;
  huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_SetTxFifoThreshold(&huart2, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_SetRxFifoThreshold(&huart2, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK)
  {
    Error_Handler();
  }
  if (HAL_UARTEx_DisableFifoMode(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */
#endif
}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
#ifndef HOST_SIMULATION
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);

  /*Configure GPIO pin : PA5 */
  GPIO_InitStruct.Pin = GPIO_PIN_5;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
#endif
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

 /* MPU Configuration */

void MPU_Config(void)
{
#ifndef HOST_SIMULATION
  MPU_Region_InitTypeDef MPU_InitStruct = {0};

  /* Disables the MPU */
  HAL_MPU_Disable();

  /** Initializes and configures the Region and the memory to be protected
  */
  MPU_InitStruct.Enable = MPU_REGION_ENABLE;
  MPU_InitStruct.Number = MPU_REGION_NUMBER0;
  MPU_InitStruct.BaseAddress = 0x0;
  MPU_InitStruct.Size = MPU_REGION_SIZE_4GB;
  MPU_InitStruct.SubRegionDisable = 0x87;
  MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
  MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
  MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
  MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
  MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;

  HAL_MPU_ConfigRegion(&MPU_InitStruct);
  /* Enables the MPU */
  HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
#endif
}

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
