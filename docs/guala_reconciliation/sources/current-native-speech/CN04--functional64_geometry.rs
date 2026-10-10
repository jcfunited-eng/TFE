//! Existing64-column physical incidence with its recovered resting transmission.
//! Baselines are immutable anatomy; signed persistent plastic rows are separate.
use std::sync::Arc;
pub(crate) const NODES:usize=20_480;
pub(crate) const INTRA:usize=2_621_440;
pub(crate) const INTER23:usize=67_108_864;
pub(crate) const INTER5:usize=16_777_216;
pub(crate) const RAW_SLOTS:usize=INTRA+INTER23+INTER5;
const BLOCKS:[(usize,usize,usize,usize,usize);6]=[
    (160,64,32,128,0),(32,128,32,128,8192),(32,128,224,64,24576),
    (224,64,288,32,32768),(288,32,160,64,34816),(0,32,32,128,36864),
];
#[derive(Clone,Copy,Debug)]
pub(crate) struct Contact{pub(crate) from:u16,pub(crate) to:u16,pub(crate) authentic_slot:u32,pub(crate) threshold:f64,pub(crate) plastic:bool}
#[derive(Clone,Debug)]
pub(crate) struct Geometry{
    pub(crate) severed:Arc<[bool]>,pub(crate) yield_intra:[f64;64],pub(crate) yield_inter:f64,
    degrees:Arc<[u32]>,baseline_inverse:Arc<[[f64;3]]>,mounted_count:usize,
}
fn upper(x:f64)->f64{if x==0.0{0.0}else{f64::from_bits(x.to_bits()+1)}}
impl Geometry{
    pub(crate) fn new(severed:Arc<[bool]>,yield_intra:[f64;64],yield_inter:f64)->Result<Self,&'static str>{
        if severed.len()!=4096||yield_intra.iter().chain(std::iter::once(&yield_inter)).any(|x|!x.is_finite()||*x<=0.0){return Err("invalid retained contact geometry");}
        let mut g=Self{severed,yield_intra,yield_inter,degrees:vec![0;NODES].into(),baseline_inverse:vec![[0.0;3];NODES].into(),mounted_count:0};
        let mut degrees=vec![0u32;NODES];
        for column in 0..64{
            for &(_,send_n,to,recv_n,_)in &BLOCKS{for j in 0..recv_n{degrees[column*320+to+j]+=send_n as u32;}}
            for from in 0..64{if !g.fasciculated(from,column){continue;}
                for j in 0..128{degrees[column*320+32+j]+=(0..128).filter(|&i|mask23(i,j)).count() as u32;}
                for j in 0..64{degrees[column*320+224+j]+=(0..64).filter(|&i|mask5(i,j)).count() as u32;}
            }
        }
        g.mounted_count=degrees.iter().map(|&n|n as usize).sum();g.degrees=degrees.into();
        let mut bounds=vec![[0.0;3];NODES];
        let mut add=|from:usize,to:usize,b:f64|{
            let inv=upper(1.0/g.degrees[to] as f64);let first=upper(b*inv);let second=upper(b*first);
            bounds[from][0]=upper(bounds[from][0]+second);bounds[from][1]=upper(bounds[from][1]+first);
            bounds[to][2]=upper(bounds[to][2]+first);
        };
        for c in 0..64{
            for j in 0..128{add(c*320+160+j/2,c*320+32+j,0.5);}
            for j in 0..64{add(c*320+32+2*j,c*320+224+j,0.5);}
            for j in 0..32{add(c*320+224+2*j,c*320+288+j,0.5);}
            for to in 0..64{if !g.fasciculated(c,to){continue;}
                let b=crate::cortical_column::G_ELASTIC_BASELINE as f64;
                for i in 0..128{for j in 0..128{if mask23(i,j){add(c*320+32+i,to*320+32+j,b);}}}
                for i in 0..64{for j in 0..64{if mask5(i,j){add(c*320+224+i,to*320+224+j,b);}}}
            }
        }
        if bounds.iter().flatten().any(|x|!x.is_finite()){return Err("nonfinite baseline geometry bound");}
        g.baseline_inverse=bounds.into();Ok(g)
    }
    pub(crate) fn fasciculated(&self,from:usize,to:usize)->bool {
        if from>=64||to>=64||from==to||self.severed[from*64+to]{return false;}
        let a=from/8;let b=to/8;if a==b{return true;}
        matches!((a,b),(0,3)|(3,0)|(1,4)|(4,1)|(2,3)|(3,2)|(2,6)|(6,2)|
            (3,5)|(5,3)|(3,7)|(7,3)|(4,5)|(5,4)|(4,7)|(7,4)|(6,7)|(7,6)|
            (6,5)|(5,6)|(7,5)|(5,7)|(5,0)|(5,1))
    }
    pub(crate) fn contact(&self,slot:usize)->Option<Contact> {
        if slot>=RAW_SLOTS{return None;}
        if slot<INTRA {
            let column=slot/40960;let within=slot%40960;
            for &(from,sn,to,rn,offset) in &BLOCKS {
                if within>=offset&&within<offset+sn*rn {
                    let k=within-offset;let i=k/rn;let j=k%rn;
                    return Some(Contact{from:(column*320+from+i) as u16,to:(column*320+to+j) as u16,
                        authentic_slot:slot as u32,threshold:self.yield_intra[column],plastic:!(from==32&&to==32&&i==j)});
                }
            }
            return None;
        }
        let (raw,n,offset)=if slot<INTRA+INTER23{(slot-INTRA,128,32)}else{(slot-INTRA-INTER23,64,224)};
        let pair=raw/(n*n);let k=raw%(n*n);let fc=pair/64;let tc=pair%64;let i=k/n;let j=k%n;
        if !self.fasciculated(fc,tc)||(n==128&&!mask23(i,j))||(n==64&&!mask5(i,j)){return None;}
        Some(Contact{from:(fc*320+offset+i) as u16,to:(tc*320+offset+j) as u16,
            authentic_slot:slot as u32,threshold:self.yield_inter,plastic:true})
    }
    pub(crate) fn between(&self,from:usize,to:usize)->Option<Contact> {
        if from>=NODES||to>=NODES{return None;}
        let fc=from/320;let tc=to/320;let i=from%320;let j=to%320;
        if fc==tc {
            for &(a,sn,b,rn,offset) in &BLOCKS {
                if i>=a&&i<a+sn&&j>=b&&j<b+rn{return self.contact(fc*40960+offset+(i-a)*rn+j-b);}
            }
            return None;
        }
        if (32..160).contains(&i)&&(32..160).contains(&j) {
            self.contact(INTRA+(fc*64+tc)*16384+(i-32)*128+j-32)
        }else if (224..288).contains(&i)&&(224..288).contains(&j) {
            self.contact(INTRA+INTER23+(fc*64+tc)*4096+(i-224)*64+j-224)
        }else{None}
    }
    pub(crate) fn degree(&self,node:usize)->u32{self.degrees[node]}
    pub(crate) fn mounted_count(&self)->usize{self.mounted_count}
    pub(crate) fn edge_lambda(&self,contact:Contact,lambda:f64)->f64{lambda/self.degrees[contact.to as usize] as f64}
    pub(crate) fn baseline(&self,e:Contact)->f64{
        if e.from as usize/320!=e.to as usize/320{return crate::cortical_column::G_ELASTIC_BASELINE as f64;}
        let i=e.from as usize%320;let j=e.to as usize%320;
        if (160..224).contains(&i)&&(32..160).contains(&j)&&i-160==(j-32)/2
            ||(32..160).contains(&i)&&(224..288).contains(&j)&&i-32==2*(j-224)
            ||(224..288).contains(&i)&&(288..320).contains(&j)&&i-224==2*(j-288){0.5}else{0.0}
    }
    pub(crate) fn baseline_inverse_bounds(&self,node:usize)->[f64;3]{self.baseline_inverse[node]}
    pub(crate) fn incoming_baseline_max(&self,node:usize)->f64{if (32..160).contains(&(node%320))||(224..320).contains(&(node%320)){0.5}else{0.0}}
    pub(crate) fn baseline_zero_incoming_count(&self,node:usize)->u32{
        let local=node%320;let intra:u32=BLOCKS.iter().filter(|&&(_,_,to,n,_)|(to..to+n).contains(&local)).map(|&(_,n,_,_,_)|n as u32).sum();
        intra-u32::from(self.incoming_baseline_max(node)!=0.0)
    }
    pub(crate) fn baseline_intra_neighbors(node:usize)->[Option<usize>;3]{
        let c=node/320*320;let i=node%320;
        if (160..224).contains(&i){let j=i-160;[Some(c+32+2*j),Some(c+33+2*j),None]}
        else if (32..160).contains(&i){let j=i-32;[Some(c+160+j/2),if j%2==0{Some(c+224+j/2)}else{None},None]}
        else if (224..288).contains(&i){let j=i-224;[Some(c+32+2*j),if j%2==0{Some(c+288+j/2)}else{None},None]}
        else if (288..320).contains(&i){[Some(c+224+2*(i-288)),None,None]}else{[None;3]}
    }
    pub(crate) fn inter_mask(local:usize,width:usize)->Result<[u64;2],&'static str>{
        let(r,m)=match width{128=>(12,16),64=>(6,8),_=>return Err("inter mask width")};
        if local>=width{return Err("inter mask local address");}
        let mut bits=[0u64;2];
        for j in local.saturating_sub(r)..(local+r+1).min(width){bits[j/64]|=1u64<<(j%64);}
        for j in (local%m..width).step_by(m){bits[j/64]|=1u64<<(j%64);}
        Ok(bits)
    }
}
fn mask23(i:usize,j:usize)->bool{i.abs_diff(j)<=12||i%16==j%16}
fn mask5(i:usize,j:usize)->bool{i.abs_diff(j)<=6||i%8==j%8}

impl Geometry{
    /// Enumerate actual incoming anatomy only after a proven receiver stress
    /// range admits a possible yield. No persistent zero-edge table is built.
    pub(crate) fn visit_incoming<F>(&self,to:usize,mut visit:F)->Result<(),&'static str>
    where F:FnMut(Contact)->Result<(),&'static str>{
        if to>=NODES{return Err("incoming node address");}
        let column=to/320;let within=to%320;
        for &(from,sn,start,rn,offset)in &BLOCKS{
            if(start..start+rn).contains(&within){
                let j=within-start;
                for i in 0..sn{
                    let slot=column*40960+offset+i*rn+j;
                    visit(Contact{from:(column*320+from+i)as u16,to:to as u16,authentic_slot:slot as u32,
                        threshold:self.yield_intra[column],plastic:!(from==32&&start==32&&i==j)})?;
                }
            }
        }
        if(32..160).contains(&within){
            let j=within-32;
            for from in 0..64{if self.fasciculated(from,column){for i in 0..128{if mask23(i,j){
                visit(Contact{from:(from*320+32+i)as u16,to:to as u16,authentic_slot:(INTRA+(from*64+column)*16384+i*128+j)as u32,
                    threshold:self.yield_inter,plastic:true})?;
            }}}}
        }else if(224..288).contains(&within){
            let j=within-224;
            for from in 0..64{if self.fasciculated(from,column){for i in 0..64{if mask5(i,j){
                visit(Contact{from:(from*320+224+i)as u16,to:to as u16,authentic_slot:(INTRA+INTER23+(from*64+column)*4096+i*64+j)as u32,
                    threshold:self.yield_inter,plastic:true})?;
            }}}}
        }
        Ok(())
    }
    pub(crate) fn minimum_incoming_yield(&self,to:usize)->f64{self.yield_intra[to/320].min(self.yield_inter)}
}
