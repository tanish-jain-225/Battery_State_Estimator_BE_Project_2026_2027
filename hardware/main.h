#ifndef MAIN_H
#define MAIN_H

#ifndef __arm__
// Host simulation mocks (when compiled on a desktop PC)
#define HOST_SIMULATION

#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>

// Mock HAL status definitions
typedef enum {
    HAL_OK       = 0x00U,
    HAL_ERROR    = 0x01U,
    HAL_BUSY     = 0x02U,
    HAL_TIMEOUT  = 0x03U
} HAL_StatusTypeDef;

// Mock UART definitions
typedef struct {
    uint32_t Instance;
    struct {
        uint32_t BaudRate;
        uint32_t WordLength;
        uint32_t StopBits;
        uint32_t Parity;
        uint32_t Mode;
        uint32_t HwFlowCtl;
        uint32_t OverSampling;
        uint32_t OneBitSampling;
        uint32_t ClockPrescaler;
    } Init;
    struct {
        uint32_t AdvFeatureInit;
    } AdvancedInit;
} UART_HandleTypeDef;

#define USART2                              ((void*)0x40004400)
#define UART_WORDLENGTH_8B                  8
#define UART_STOPBITS_1                     1
#define UART_PARITY_NONE                    0
#define UART_MODE_TX_RX                     3
#define UART_HWCONTROL_NONE                 0
#define UART_OVERSAMPLING_16                16
#define UART_ONE_BIT_SAMPLE_DISABLE         0
#define UART_PRESCALER_DIV1                 1
#define UART_ADVFEATURE_NO_INIT             0
#define UART_TXFIFO_THRESHOLD_1_8           0
#define UART_RXFIFO_THRESHOLD_1_8           0
#define HAL_MAX_DELAY                       0xFFFFFFFFU

// Mock GPIO definitions
typedef struct {
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
} GPIO_InitTypeDef;

#define GPIO_PIN_5                          ((uint16_t)0x0020)
#define GPIO_PIN_RESET                      0
#define GPIO_PIN_SET                        1

#define GPIOA                               ((void*)0x40020000)

#define GPIO_MODE_OUTPUT_PP                 1
#define GPIO_NOPULL                         0
#define GPIO_SPEED_FREQ_LOW                 0

// Mock MPU and Power configurations
#define MPU_REGION_ENABLE                   1
#define MPU_REGION_NUMBER0                  0
#define MPU_REGION_SIZE_4GB                 0
#define MPU_TEX_LEVEL0                      0
#define MPU_REGION_NO_ACCESS                0
#define MPU_INSTRUCTION_ACCESS_DISABLE      0
#define MPU_ACCESS_SHAREABLE                0
#define MPU_ACCESS_NOT_CACHEABLE            0
#define MPU_ACCESS_NOT_BUFFERABLE           0
#define MPU_PRIVILEGED_DEFAULT              0

#define PWR_LDO_SUPPLY                      0
#define PWR_REGULATOR_VOLTAGE_SCALE2        0
#define PWR_FLAG_VOSRDY                     0

typedef struct {
    uint32_t Enable;
    uint32_t Number;
    uint32_t BaseAddress;
    uint32_t Size;
    uint32_t SubRegionDisable;
    uint32_t TypeExtField;
    uint32_t AccessPermission;
    uint32_t DisableExec;
    uint32_t IsShareable;
    uint32_t IsCacheable;
    uint32_t IsBufferable;
} MPU_Region_InitTypeDef;

typedef struct {
    uint32_t OscillatorType;
    uint32_t HSIState;
    uint32_t HSICalibrationValue;
    struct {
        uint32_t PLLState;
        uint32_t PLLSource;
        uint32_t PLLM;
        uint32_t PLLN;
        uint32_t PLLP;
        uint32_t PLLQ;
        uint32_t PLLR;
        uint32_t PLLRGE;
        uint32_t PLLVCOSEL;
        uint32_t PLLFRACN;
    } PLL;
} RCC_OscInitTypeDef;

typedef struct {
    uint32_t ClockType;
    uint32_t SYSCLKSource;
    uint32_t SYSCLKDivider;
    uint32_t AHBCLKDivider;
    uint32_t APB3CLKDivider;
    uint32_t APB1CLKDivider;
    uint32_t APB2CLKDivider;
    uint32_t APB4CLKDivider;
} RCC_ClkInitTypeDef;

#define RCC_OSCILLATORTYPE_HSI              1
#define RCC_HSI_DIV1                        1
#define RCC_PLL_ON                          1
#define RCC_PLLSOURCE_HSI                   1
#define RCC_PLL1VCIRANGE_3                  3
#define RCC_PLL1VCOWIDE                     1
#define RCC_CLOCKTYPE_HCLK                  1
#define RCC_CLOCKTYPE_SYSCLK                2
#define RCC_CLOCKTYPE_PCLK1                 4
#define RCC_CLOCKTYPE_PCLK2                 8
#define RCC_CLOCKTYPE_D3PCLK1               16
#define RCC_CLOCKTYPE_D1PCLK1               32
#define RCC_SYSCLKSOURCE_PLLCLK             2
#define RCC_SYSCLK_DIV1                     1
#define RCC_HCLK_DIV2                       2
#define RCC_APB3_DIV2                       2
#define RCC_APB1_DIV2                       2
#define RCC_APB2_DIV2                       2
#define RCC_APB4_DIV2                       2
#define FLASH_LATENCY_1                     1

// Mock Function APIs
static inline void HAL_Init(void) {}
static inline void HAL_MPU_Disable(void) {}
static inline void HAL_MPU_ConfigRegion(MPU_Region_InitTypeDef* init) {}
static inline void HAL_MPU_Enable(uint32_t priv) {}
static inline void HAL_PWREx_ConfigSupply(uint32_t supply) {}
static inline void __HAL_PWR_VOLTAGESCALING_CONFIG(uint32_t scale) {}
static inline uint32_t __HAL_PWR_GET_FLAG(uint32_t flag) { return 1; }
static inline HAL_StatusTypeDef HAL_RCC_OscConfig(RCC_OscInitTypeDef* init) { return HAL_OK; }
static inline HAL_StatusTypeDef HAL_RCC_ClockConfig(RCC_ClkInitTypeDef* init, uint32_t latency) { return HAL_OK; }

static inline void HAL_GPIO_Init(void* GPIOx, GPIO_InitTypeDef* init) {}
static inline void HAL_GPIO_WritePin(void* GPIOx, uint16_t Pin, int PinState) {
    // Print LED state to stdout for verification
    if (PinState == GPIO_PIN_SET) {
        printf(" [LED: RED/ON]\n");
    } else {
        printf(" [LED: GREEN/OFF]\n");
    }
}
static inline void HAL_GPIO_TogglePin(void* GPIOx, uint16_t Pin) {
    static bool state = false;
    state = !state;
    printf(" [LED: TOGGLED to %s]\n", state ? "ON" : "OFF");
}

static inline void HAL_Delay(uint32_t Delay) {
    // Bypass delay in host simulation to run instantly
}

static inline HAL_StatusTypeDef HAL_UART_Init(UART_HandleTypeDef* huart) { return HAL_OK; }
static inline HAL_StatusTypeDef HAL_UARTEx_SetTxFifoThreshold(UART_HandleTypeDef* huart, uint32_t threshold) { return HAL_OK; }
static inline HAL_StatusTypeDef HAL_UARTEx_SetRxFifoThreshold(UART_HandleTypeDef* huart, uint32_t threshold) { return HAL_OK; }
static inline HAL_StatusTypeDef HAL_UARTEx_DisableFifoMode(UART_HandleTypeDef* huart) { return HAL_OK; }

static inline HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef* huart, const uint8_t* pData, uint16_t Size, uint32_t Timeout) {
    for (uint16_t i = 0; i < Size; i++) {
        putchar(pData[i]);
    }
    return HAL_OK;
}

static inline void __disable_irq(void) {}
static inline void __HAL_RCC_GPIOC_CLK_ENABLE(void) {}
static inline void __HAL_RCC_GPIOA_CLK_ENABLE(void) {}

// Error handler prototype
void Error_Handler(void);

#else
// Real STM32 headers if compiling for the actual target hardware
#include "stm32h7xx_hal.h"
#endif

#endif // MAIN_H
