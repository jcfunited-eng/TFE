//! Exact custody of admitted work. Sole store quantum: 1/(125*2^1127)J.
//! This module is a component of the unreviewed complete material candidate.
//! It neither creates nutrition nor assigns an electrical integral to heat.
use std::cmp::Ordering;

pub(crate) const LIMBS:usize=19;
pub(crate) const CUT_BITS:usize=52;
pub(crate) const FULL_TICKS:u64=1u64<<CUT_BITS;
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) struct Work {pub(crate) limbs:[u64;LIMBS]}
impl Work {
    pub(crate) const ZERO:Self=Self{limbs:[0;LIMBS]};
    pub(crate) fn from_u64(n:u64)->Self{let mut x=Self::ZERO;x.limbs[0]=n;x}
    pub(crate) fn is_zero(self)->bool{self.limbs.iter().all(|&x|x==0)}
    pub(crate) fn cmp(self,other:Self)->Ordering{
        for i in(0..LIMBS).rev(){let c=self.limbs[i].cmp(&other.limbs[i]);if c!=Ordering::Equal{return c;}}Ordering::Equal
    }
    pub(crate) fn gte(self,other:Self)->bool{self.cmp(other)!=Ordering::Less}
    pub(crate) fn add(self,other:Self)->Result<Self,&'static str>{
        let mut next=Self::ZERO;let mut carry=0u128;
        for i in 0..LIMBS{let n=self.limbs[i]as u128+other.limbs[i]as u128+carry;next.limbs[i]=n as u64;carry=n>>64;}
        if carry!=0{Err("exact work addition overflow")}else{Ok(next)}
    }
    pub(crate) fn sub(self,other:Self)->Result<Self,&'static str>{
        if !self.gte(other){return Err("exact work underflow");}
        let mut next=Self::ZERO;let mut borrow=false;
        for i in 0..LIMBS{let(a,b)=self.limbs[i].overflowing_sub(other.limbs[i]);let(c,d)=a.overflowing_sub(u64::from(borrow));next.limbs[i]=c;borrow=b||d;}Ok(next)
    }
    pub(crate) fn mul(self,n:u64)->Result<Self,&'static str>{
        let mut next=Self::ZERO;let mut carry=0u128;
        for i in 0..LIMBS{let x=self.limbs[i]as u128*n as u128+carry;next.limbs[i]=x as u64;carry=x>>64;}
        if carry!=0{Err("exact work product overflow")}else{Ok(next)}
    }
    pub(crate) fn shl(self,n:usize)->Result<Self,&'static str>{
        if self.is_zero(){return Ok(self);}
        if n>=64*LIMBS||self.bits().checked_add(n).map_or(true,|x|x>64*LIMBS){return Err("exact work shift overflow");}
        let mut next=Self::ZERO;let words=n/64;let bits=n%64;
        for i in 0..LIMBS-words{next.limbs[i+words]|=self.limbs[i]<<bits;if bits!=0&&i+words+1<LIMBS{next.limbs[i+words+1]|=self.limbs[i]>>(64-bits);}}
        Ok(next)
    }
    pub(crate) fn shr(self,n:usize)->Self{
        if n>=64*LIMBS{return Self::ZERO;}let mut next=Self::ZERO;let words=n/64;let bits=n%64;
        for i in words..LIMBS{next.limbs[i-words]|=self.limbs[i]>>bits;if bits!=0&&i>words{next.limbs[i-words-1]|=self.limbs[i]<<(64-bits);}}next
    }
    pub(crate) fn low_zero(self,n:usize)->bool{
        if n>=64*LIMBS{return self.is_zero();}
        let words=n/64;self.limbs[..words].iter().all(|&x|x==0)&&(n%64==0||self.limbs[words]&((1u64<<(n%64))-1)==0)
    }
    pub(crate) fn exact_div_small(self,n:u64)->Result<Self,&'static str>{
        if n==0{return Err("zero work divisor");}let mut next=Self::ZERO;let mut rem=0u128;
        for i in(0..LIMBS).rev(){let x=(rem<<64)|self.limbs[i]as u128;next.limbs[i]=(x/n as u128)as u64;rem=x%n as u128;}
        if rem==0{Ok(next)}else{Err("unsupported work denominator")}
    }
    pub(crate) fn bits(self)->usize{
        for i in(0..LIMBS).rev(){if self.limbs[i]!=0{return i*64+(64-self.limbs[i].leading_zeros()as usize);}}0
    }
    /// The finite numerical packet's bits are exact; no claim is made that
    /// binary64 arithmetic used to obtain the packet was exact real arithmetic.
    pub(crate) fn finite_joules(j:f64)->Result<Self,&'static str>{
        let(m,p)=finite_parts(j)?;
        // j=m*2^p; q^-1=125*2^1127. Minimum p is-1074.
        Self::from_u64(m).mul(125)?.shl((p+1127)as usize)
    }
    pub(crate) fn nutrition(micrograms:u64)->Result<Self,&'static str>{Self::from_u64(micrograms).mul(17)?.shl(1124)}
    /// Exact G*Vs*Vs/1000J from the declared finite material coefficient bits.
    pub(crate) fn output_regulator_interval(g:f64,vs:f64)->Result<Self,&'static str>{
        let(mg,pg)=finite_parts(g)?;let(mv,pv)=finite_parts(vs)?;
        if mg==0||mv==0{return Err("zero regulator material coefficient");}
        let n=Self::from_u64(mg).mul(mv)?.mul(mv)?;let shift=pg+2*pv+1124;
        let value=if shift>=0{n.shl(shift as usize)?}else{let bits=(-shift)as usize;if !n.low_zero(bits){return Err("regulator coefficient exceeds exact work lattice");}n.shr(bits)};
        if !value.low_zero(CUT_BITS){return Err("regulator has no exact common event grid");}Ok(value)
    }
    /// Actual integer microwatt anatomy over one actual millisecond. Refuse an
    /// unrepresented denominator; never round a different thermal anatomy.
    pub(crate) fn thermal_interval(microwatts:u64)->Result<Self,&'static str>{
        Self::from_u64(microwatts).shl(1118)?.exact_div_small(15_625)
    }
    /// Full1ms budget owned by a measured1ms or10ms packet. This performs the
    /// release division exactly, including minimum positive binary64 packets.
    pub(crate) fn packet_interval(j:f64,release_ms:u8)->Result<Self,&'static str>{
        if !matches!(release_ms,1|10){return Err("unsupported physical release duration");}
        let value=Self::finite_joules(j)?.exact_div_small(release_ms as u64)?;
        if !value.low_zero(CUT_BITS){return Err("packet has no exact common event grid");}Ok(value)
    }
    /// Every participant uses exactly the SAME n/2^52 interval fraction.
    pub(crate) fn slice(self,ticks:u64)->Result<Self,&'static str>{
        if ticks>FULL_TICKS||!self.low_zero(CUT_BITS){return Err("invalid exact work slice");}self.shr(CUT_BITS).mul(ticks)
    }
    /// Largest affordable common event-grid prefix. At most53 comparisons;
    /// only bounded exact arithmetic, never repeated material integration.
    pub(crate) fn affordable_ticks(self,interval_cost:Self)->Result<u64,&'static str>{
        if !interval_cost.low_zero(CUT_BITS){return Err("funded interval has no common event grid");}
        if interval_cost.is_zero()||self.gte(interval_cost){return Ok(FULL_TICKS);}
        let unit=interval_cost.shr(CUT_BITS);let(mut lo,mut hi)=(0,FULL_TICKS);
        while lo<hi{let mid=lo+(hi-lo+1)/2;if self.gte(unit.mul(mid)?){lo=mid}else{hi=mid-1;}}
        Ok(lo)
    }
    /// Reporting projection only. It is never used for exact affordability,
    /// source transfer, nutrition debit, thermal payment or serialization.
    pub(crate) fn projection_joules(self)->Result<f64,&'static str>{
        let bits=self.bits();if bits==0{return Ok(0.0);}
        let shift=bits.saturating_sub(53);let mut top=self.shr(shift).limbs[0];
        if shift>0{let half=shift-1;let one=(self.limbs[half/64]>>(half%64))&1;let lower=!self.low_zero(half);if one!=0&&(lower||top&1!=0){top+=1;}}
        // Decompose to avoid underflowing2^(shift-1127) before multiplication.
        // The first factor is a normalized finite significand in[1,2].
        let top_bits=64-top.leading_zeros()as usize;let exponent=shift as i32+top_bits as i32-1-1127;
        let significand=top as f64/(1u64<<(top_bits-1))as f64;
        let scaled=if exponent>=-1022{significand*f64::from_bits(((exponent+1023)as u64)<<52)}else{
            let e=exponent+1074;if e<0{0.0}else{significand*(1u64<<e as usize)as f64*f64::from_bits(1)}
        };
        let value=scaled/125.0;if value.is_finite(){Ok(value)}else{Err("work reporting projection overflow")}
    }
}
fn finite_parts(value:f64)->Result<(u64,i32),&'static str>{
    if !value.is_finite()||value<0.0{return Err("negative or nonfinite work coefficient");}
    let b=value.to_bits();let e=((b>>52)&2047)as i32;let f=b&((1u64<<52)-1);
    Ok(if e==0{(f,-1074)}else{(f|(1u64<<52),e-1075)})
}
