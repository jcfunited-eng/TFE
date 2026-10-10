//! Exact custody of admitted finite charge packets. Numerical capacitor voltage
//! is a projection of this retained charge, not a replacement for its bits.
use crate::mathloom::Uint1152;
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) struct Charge {pub(crate) negative:bool,pub(crate) magnitude:Uint1152}
impl Charge {
    pub(crate) const ZERO:Self=Self{negative:false,magnitude:Uint1152::ZERO};
    pub(crate) fn validate(self)->Result<(),&'static str>{
        if self.negative&&self.magnitude.is_zero(){Err("noncanonical charge zero")}else{Ok(())}
    }
    pub(crate) fn packet(value:f64)->Result<Self,&'static str>{
        if !value.is_finite(){return Err("nonfinite charge packet");}
        let bits=value.to_bits();let exponent=((bits>>52)&2047)as usize;
        let mantissa=(bits&((1u64<<52)-1))|if exponent==0{0}else{1u64<<52};
        let magnitude=Uint1152::from_u64(mantissa).shl(if exponent==0{0}else{exponent-1})
            .map_err(|_|"charge packet exceeds exact custody")?;
        Ok(Self{negative:bits>>63!=0&&!magnitude.is_zero(),magnitude})
    }
    pub(crate) fn add(self,other:Self)->Result<Self,&'static str>{
        self.validate()?;other.validate()?;
        let(magnitude,negative)=if self.negative==other.negative{
            let mut out=Uint1152::ZERO;let mut carry=0u128;
            for i in 0..18{let sum=self.magnitude.limbs[i]as u128+other.magnitude.limbs[i]as u128+carry;out.limbs[i]=sum as u64;carry=sum>>64;}
            if carry!=0{return Err("charge custody overflow");}(out,self.negative)
        }else if self.magnitude.gte(&other.magnitude){
            (self.magnitude.sub(&other.magnitude).map_err(|_|"charge difference")?,self.negative)
        }else{(other.magnitude.sub(&self.magnitude).map_err(|_|"charge difference")?,other.negative)};
        Ok(Self{negative:negative&&!magnitude.is_zero(),magnitude})
    }
    pub(crate) fn neg(self)->Self{Self{negative:!self.negative&&!self.magnitude.is_zero(),magnitude:self.magnitude}}
    pub(crate) fn add_packet(self,value:f64)->Result<Self,&'static str>{self.add(Self::packet(value)?)}
    /// Correctly rounded ties-to-even binary64 projection by bit construction.
    /// No intermediate power-of-two underflow loses retained subnormal charge.
    pub(crate) fn projection(self)->Result<f64,&'static str>{
        self.validate()?;let length=self.magnitude.bit_length()as usize;
        if length==0{return Ok(0.0);}
        if length<=52{let bits=self.magnitude.limbs[0]|if self.negative{1u64<<63}else{0};return Ok(f64::from_bits(bits));}
        let mut shift=length-53;let mut top=self.magnitude.shr(shift).limbs[0];
        if shift>0{
            let half_index=shift-1;let half=(self.magnitude.limbs[half_index/64]>>(half_index%64))&1;
            let mut lower=self.magnitude.limbs[..half_index/64].iter().any(|&x|x!=0);
            if half_index%64>0{lower|=(self.magnitude.limbs[half_index/64]&((1u64<<(half_index%64))-1))!=0;}
            if half!=0&&(lower||top&1!=0){top+=1;}
        }
        if top==(1u64<<53){top>>=1;shift+=1;}
        let exponent=shift+1;if exponent>=2047{return Err("charge projection overflow");}
        Ok(f64::from_bits(((exponent as u64)<<52)|(top&((1u64<<52)-1))|if self.negative{1u64<<63}else{0}))
    }
}
