"""Frame builder / parser for the ESN-EKF-UKF platform UART protocol (see esn_platform.v)."""
import struct
SYNC=0xA5
CMD_WRITE,CMD_CTRL,CMD_STEP,CMD_PING=1,2,3,4
T_WIN,T_W,T_IN,T_BIAS,T_RO_SOC,T_RO_SOH,T_EKF_REG,T_UKF_REG,T_EKF_OCV,T_EKF_SLOPE,T_UKF_OCV,T_UKF_SLOPE=0,1,2,3,4,5,8,9,10,11,12,13
WB={T_WIN:2,T_W:2,T_IN:2,T_BIAS:2,T_RO_SOC:4,T_RO_SOH:4}

def frame(cmd,payload=b""):
    body=bytes([cmd,len(payload)&255,len(payload)>>8])+bytes(payload)
    return bytes([SYNC])+body+bytes([sum(body)&255])

def write_frames(target,start,words,chunk=200):
    """words: ints (two's complement handled here). Returns list of frames."""
    wb=WB.get(target,4); out=[]
    for i in range(0,len(words),chunk):
        part=words[i:i+chunk]
        pl=bytes([target,wb])+struct.pack("<H",start+i)
        for w in part: pl+=(int(w)&((1<<(8*wb))-1)).to_bytes(wb,"little")
        out.append(frame(CMD_WRITE,pl))
    return out

def ctrl_frame(clear=False,init=False): return frame(CMD_CTRL,bytes([int(clear)|(int(init)<<1)]))
def ping_frame(): return frame(CMD_PING)
def step_frame(u,i_q28,v_q28):
    pl=b"".join(struct.pack("<h",int(x)) for x in u)+struct.pack("<ii",int(i_q28),int(v_q28))
    return frame(CMD_STEP,pl)

def parse_stream(data):
    """Split a response byte stream into (cmd,payload) frames; verifies checksums."""
    out=[];i=0
    while i<len(data):
        if data[i]!=SYNC: i+=1; continue
        cmd=data[i+1]; ln=data[i+2]|(data[i+3]<<8); pl=data[i+4:i+4+ln]; chk=data[i+4+ln]
        if (cmd+data[i+2]+data[i+3]+sum(pl))&255!=chk: raise ValueError("bad checksum at byte %d"%i)
        out.append((cmd,bytes(pl))); i+=5+ln
    return out

def decode_step(pl):
    s=lambda b,n=None:int.from_bytes(b,"little",signed=True)
    return dict(step=pl[0],soh_valid=pl[1]&1,ovf=(pl[1]>>1)&1,soc_esn=s(pl[2:4]),soc_ekf=s(pl[4:8]),soc_ukf=s(pl[8:12]),
                soh=s(pl[12:14]),cyc_esn=int.from_bytes(pl[14:17],"little"),cyc_ekf=int.from_bytes(pl[17:19],"little"),
                cyc_ukf=int.from_bytes(pl[19:21],"little"))
