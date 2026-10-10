//! Reciprocal resting contacts, exact sparse override exclusion and bounded
//! positive moment arithmetic. No persistent state or independent clock.
use super::*;
#[derive(Clone,Copy,Debug)]
struct Moment{weight:f64,mean:f64,m2:f64,w:Interval,s:Interval,s2:Interval}
impl Moment{
    fn empty()->Self{Self{weight:0.0,mean:0.0,m2:0.0,w:Interval::point(0.0),s:Interval::point(0.0),s2:Interval::point(0.0)}}
    fn leaf(x:f64,weight:f64)->Result<Self>{
        finite(x)?;nonnegative(weight)?;
        if weight==0.0{return Ok(Self::empty());}
        let w=Interval::point(weight);let x=Interval::point(x);
        Ok(Self{weight,mean:x.lo,m2:0.0,w,s:w.mul(x),s2:w.mul(square(x))})
    }
    fn merge(self,b:Self,count:&mut WorkCount,admission:Admission)->Result<Self>{
        if self.weight==0.0{return Ok(b);}if b.weight==0.0{return Ok(self);}
        count.force(1,admission)?;
        let weight=finite(self.weight+b.weight)?;let delta=finite(b.mean-self.mean)?;
        let ratio=finite(b.weight/weight)?;let mean=finite(self.mean+ratio*delta)?;
        let m2=nonnegative((self.m2+b.m2)+(self.weight*ratio)*(delta*delta))?;
        let result=Self{weight,mean,m2,w:self.w.add(b.w),s:self.s.add(b.s),s2:self.s2.add(b.s2)};
        valid(result.w)?;valid(result.s)?;valid(result.s2)?;Ok(result)
    }
}
#[derive(Clone)]struct Tree{width:usize,nodes:Vec<Moment>}
impl Tree{
    fn new(values:&[f64],weights:&[f64],count:&mut WorkCount,admission:Admission)->Result<Self>{
        let n=values.len();if !matches!(n,64|128)||weights.len()!=n{return Err(MaterialError::Invalid("contact tree anatomy"));}
        count.force(n,admission)?;let mut nodes=vec![Moment::empty();2*n];
        for i in 0..n{nodes[n+i]=Moment::leaf(values[i],weights[i])?;}
        for i in(1..n).rev(){nodes[i]=nodes[2*i].merge(nodes[2*i+1],count,admission)?;}
        Ok(Self{width:n,nodes})
    }
    fn query(&self,bits:[u64;2],count:&mut WorkCount,admission:Admission)->Result<Moment>{
        fn occupied_in(bits:[u64;2],lo:usize,width:usize)->usize{
            let mut occupied=0usize;
            for word in 0..2{let left=lo.max(word*64);let right=(lo+width).min((word+1)*64);
                if left<right{let length=right-left;let mask=if length==64{u64::MAX}else{((1u64<<length)-1)<<(left%64)};occupied+=(bits[word]&mask).count_ones()as usize;}}
            occupied
        }
        fn walk(tree:&Tree,index:usize,lo:usize,width:usize,bits:[u64;2],occupied:usize,count:&mut WorkCount,a:Admission)->Result<Moment>{
            if occupied==0{return Ok(Moment::empty());}if occupied==width{return Ok(tree.nodes[index]);}
            count.force(1,a)?;
            if width==1{return Err(MaterialError::Invalid("contact mask leaf"));}
            let half=width/2;let left_occupied=occupied_in(bits,lo,half);let right_occupied=occupied-left_occupied;
            // Empty-child merges return the other operand unchanged. Do not
            // visit that empty child or perform its identity merge. Carry the
            // exact child occupancy; retain all nonempty lower/upper grouping.
            if left_occupied==0{return walk(tree,index*2+1,lo+half,half,bits,right_occupied,count,a);}
            if right_occupied==0{return walk(tree,index*2,lo,half,bits,left_occupied,count,a);}
            let left=walk(tree,index*2,lo,half,bits,left_occupied,count,a)?;
            let right=walk(tree,index*2+1,lo+half,half,bits,right_occupied,count,a)?;
            left.merge(right,count,a)
        }
        walk(self,1,0,self.width,bits,occupied_in(bits,0,self.width),count,admission)
    }
}
impl Tree{
    fn contiguous(&self,left:usize,right:usize,count:&mut WorkCount,a:Admission)->Result<Moment>{
        if left>=right||right>self.width{return Err(MaterialError::Invalid("contact band interval"));}
        fn walk(tree:&Tree,left:usize,right:usize,count:&mut WorkCount,a:Admission)->Result<Moment>{
            let differing=left^(right-1);
            let width=if differing==0{1}else{1usize<<(usize::BITS-differing.leading_zeros())};
            let lo=left&!(width-1);let index=(tree.width+lo)/width;
            if left==lo&&right==lo+width{return Ok(tree.nodes[index]);}
            count.force(1,a)?;
            let middle=lo+width/2;
            // The lowest common subtree has two occupied children. The
            // original query's skipped ancestors returned this value verbatim.
            let lower=walk(tree,left,middle,count,a)?;
            let upper=walk(tree,middle,right,count,a)?;
            lower.merge(upper,count,a)
        }
        walk(self,left,right,count,a)
    }
    fn residue_without_self(&self,count:&mut WorkCount,a:Admission)->Result<Vec<Moment>>{
        let modulus=match self.width{128=>16,64=>8,_=>return Err(MaterialError::Invalid("contact residue anatomy"))};
        let mut result=vec![Moment::empty();self.width];
        // Both existing masks contain exactly eight congruent sites. Removing
        // empty branches preserves the original lower-to-upper nonempty merge
        // order, including every selected and outward-rounded summary bit.
        for residue in 0..modulus{
            count.force(8,a)?;let mut nodes=vec![Moment::empty();16];
            for i in 0..8{nodes[8+i]=self.nodes[self.width+residue+i*modulus];}
            for i in(1..8).rev(){nodes[i]=nodes[2*i].merge(nodes[2*i+1],count,a)?;}
            let compact=Tree{width:8,nodes};
            for i in 0..8{result[residue+i*modulus]=compact.query([255u64^(1u64<<i),0],count,a)?;}
        }Ok(result)
    }
    fn baseline_summaries(&self,count:&mut WorkCount,a:Admission)->Result<Vec<Moment>>{
        let residues=self.residue_without_self(count,a)?;let mut result=Vec::with_capacity(self.width);
        let radius=if self.width==128{12}else{6};
        for local in 0..self.width{
            let band=self.contiguous(local.saturating_sub(radius),(local+radius+1).min(self.width),count,a)?;
            result.push(band.merge(residues[local],count,a)?);}
        Ok(result)
    }
}
struct PairTrees{send:Tree,send_masks:Vec<Moment>,receive:Option<(Tree,Vec<Moment>)>}
impl PairTrees{
    fn new(send:Tree,receive:Option<Tree>,count:&mut WorkCount,a:Admission)->Result<Self>{
        let send_masks=send.baseline_summaries(count,a)?;
        let receive=match receive{Some(tree)=>{let masks=tree.baseline_summaries(count,a)?;Some((tree,masks))},None=>None};
        Ok(Self{send,send_masks,receive})
    }
    fn masked(&self,send:bool,local:usize,holes:[u64;2],count:&mut WorkCount,a:Admission)->Result<Moment>{
        let(tree,masks)=if send{(&self.send,&self.send_masks)}else{
            let(tree,masks)=self.receive.as_ref().ok_or(MaterialError::Invalid("receive summary requested from energy workspace"))?;(tree,masks)
        };
        if holes==[0;2]{count.force(1,a)?;return Ok(masks[local]);}
        query(tree,baseline_masks(local,tree.width,holes)?,count,a)
    }
}
struct Workspace{columns:Vec<Option<PairTrees>>,reached:[u64;192],adjacency:ColumnAdjacency}
fn layer(node:usize)->Option<(usize,usize,usize)>{let i=node%320;
    if(32..160).contains(&i){Some((0,32,i-32))}else if(224..288).contains(&i){Some((1,224,i-224))}else{None}}
fn width(kind:usize)->usize{if kind==0{128}else{64}}
fn pair(v:&LocalVector,f:&Frontier,s:&Functional64Material,node:usize)->PhasePair{f.pair(v,s,node)}
fn valid(i:Interval)->Result<Interval>{if !i.lo.is_finite()||!i.hi.is_finite()||i.lo>i.hi{Err(MaterialError::UnresolvedEvent("contact arithmetic enclosure"))}else{Ok(i)}}
fn square(i:Interval)->Interval{
    let low=if i.lo<=0.0&&i.hi>=0.0{0.0}else{down((i.lo*i.lo).min(i.hi*i.hi))};
    Interval{lo:low,hi:up((i.lo*i.lo).max(i.hi*i.hi))}
}
fn discrepancy(value:f64,bound:Interval)->Result<f64>{valid(bound)?;finite(up((value-bound.lo).abs().max((bound.hi-value).abs())))}
impl Workspace{
    fn new(s:&Functional64Material,f:&Frontier,a:&LocalVector,b:&LocalVector,need_receive:bool,count:&mut WorkCount,admission:Admission)->Result<Self>{
        let mut active=[false;128];let mut reached=[0u64;192];
        for &node in &f.nodes{if let Some((kind,_,local))=layer(node){
            active[2*(node/320)+kind]=true;reached[if kind==0{local}else{128+local}]|=1u64<<(node/320);
        }}
        let mut columns=(0..128).map(|_|None).collect::<Vec<_>>();
        for key in 0..128{if !active[key]{continue;}let kind=key%2;let offset=if kind==0{32}else{224};let n=width(kind);let column=key/2;
            let mut send=[0.0;128];let mut receive=[0.0;128];let mut weights=[0.0;128];let unit=[1.0;128];
            for i in 0..n{let node=column*320+offset+i;let p=pair(a,f,s,node);let q=pair(b,f,s,node);
                send[i]=0.5*(p.send.sin()+q.send.sin());
                if need_receive{receive[i]=0.5*(p.receive.sin()+q.receive.sin());weights[i]=LAMBDA/s.anatomy.geometry.degree(node)as f64;}}
            let send_tree=Tree::new(&send[..n],&unit[..n],count,admission)?;
            let receive_tree=if need_receive{Some(Tree::new(&receive[..n],&weights[..n],count,admission)?)}else{None};
            columns[key]=Some(PairTrees::new(send_tree,receive_tree,count,admission)?);
        }Ok(Self{columns,reached,adjacency:ColumnAdjacency::new()})
    }
}
struct Holes{incoming:[[u64;2];64],outgoing:[[u64;2];64],zero_incoming:u32}
impl Holes{
    fn new(s:&Functional64Material,node:usize,count:&mut WorkCount,admission:Admission)->Result<Self>{
        let mut out=Self{incoming:[[0;2];64],outgoing:[[0;2];64],zero_incoming:0};
        for &slot in s.incident.get(node).iter(){count.force(1,admission)?;
            let e=s.anatomy.contact(slot as usize)?;if *s.weights.get(slot as usize)==0.0{continue;}
            if e.to as usize==node{
                if s.anatomy.geometry.baseline(e)==0.0{out.zero_incoming=out.zero_incoming.checked_add(1).ok_or(MaterialError::Arithmetic("override ground count"))?;}
                if e.from as usize/320!=node/320{if let Some((_,_,i))=layer(e.from as usize){out.incoming[e.from as usize/320][i/64]|=1u64<<(i%64);}}
            }
            if e.from as usize==node&&e.to as usize/320!=node/320{if let Some((_,_,i))=layer(e.to as usize){out.outgoing[e.to as usize/320][i/64]|=1u64<<(i%64);}}
        }Ok(out)
    }
}
struct ReceiverStage{index:usize,node:usize,v:f64,u:f64,ds:f64,dr:f64,holes:Holes,
    incoming_moment:Moment,outgoing_moment:Moment}
fn stage_receiver(s:&Functional64Material,f:&Frontier,a:&LocalVector,b:&LocalVector,index:usize,out:&mut Forces,count:&mut WorkCount,admission:Admission)->Result<ReceiverStage>{
    let node=f.nodes[index];let holes=Holes::new(s,node,count,admission)?;let p=a.nodes[index];let q=b.nodes[index];
    let v=0.5*(p.send.sin()+q.send.sin());let u=0.5*(p.receive.sin()+q.receive.sin());let ds=dsin(p.send,q.send);let dr=dsin(p.receive,q.receive);
    let zero=s.anatomy.geometry.baseline_zero_incoming_count(node).checked_sub(holes.zero_incoming).ok_or(MaterialError::Invalid("negative baseline ground count"))?;
    if zero>0{count.force(1,admission)?;let l=LAMBDA/s.anatomy.geometry.degree(node)as f64;
        let value=l*zero as f64*u*dr;let range=Interval::point(l).mul(Interval::point(zero as f64)).mul(Interval::point(u)).mul(Interval::point(dr));out.add(index,false,value,range)?;}
    Ok(ReceiverStage{index,node,v,u,ds,dr,holes,
        incoming_moment:Moment::empty(),outgoing_moment:Moment::empty()})
}
#[derive(Clone,Copy,Debug)]pub(super) struct Energy{pub(super)value:f64,pub(super)range:Interval}
impl Energy{
    fn zero()->Self{Self{value:0.0,range:Interval::point(0.0)}}
    fn add(&mut self,value:f64,range:Interval)->Result<()>{nonnegative(value)?;valid(range)?;
        self.value=nonnegative(self.value+value)?;self.range=valid(self.range.add(range))?;Ok(())}
}
pub(super) struct Forces{pub(super)nodes:Vec<PhasePair>,pub(super)ranges:Vec<[Interval;2]>}
impl Forces{
    fn new(n:usize)->Self{Self{nodes:vec![PhasePair::default();n],ranges:vec![[Interval::point(0.0);2];n]}}
    fn add(&mut self,index:usize,send:bool,value:f64,range:Interval)->Result<()>{
        if index==usize::MAX{if value!=0.0{return Err(MaterialError::UnresolvedEvent("nonzero force outside closed contact frontier"));}return Ok(());}
        let role=if send{0}else{1};let target=if send{&mut self.nodes[index].send}else{&mut self.nodes[index].receive};
        *target=finite(*target+value)?;self.ranges[index][role]=valid(self.ranges[index][role].add(range))?;Ok(())
    }
}
fn gain(s:&Functional64Material,e:Contact)->Result<f64>{finite(s.anatomy.geometry.baseline(e)+*s.weights.get(e.authentic_slot as usize))}
fn direct_force(s:&Functional64Material,f:&Frontier,a:&LocalVector,b:&LocalVector,e:Contact,out:&mut Forces,count:&mut WorkCount,admission:Admission)->Result<()>{
    count.force(1,admission)?;let left=pair(a,f,s,e.from as usize);let right=pair(b,f,s,e.from as usize);
    let dest0=pair(a,f,s,e.to as usize);let dest1=pair(b,f,s,e.to as usize);
    let v=0.5*(left.send.sin()+right.send.sin());let u=0.5*(dest0.receive.sin()+dest1.receive.sin());let k=gain(s,e)?;let l=s.anatomy.lambda(e);
    let ds=dsin(left.send,right.send);let dr=dsin(dest0.receive,dest1.receive);let residual=u-k*v;
    let bound=Interval::point(u).sub(Interval::point(k).mul(Interval::point(v)));
    let fs=if k==0.0{0.0}else{-l*k*residual*ds};let fr=l*residual*dr;
    let bs=if k==0.0{Interval::point(0.0)}else{Interval::point(-l).mul(Interval::point(k)).mul(bound).mul(Interval::point(ds))};
    let br=Interval::point(l).mul(bound).mul(Interval::point(dr));
    out.add(f.index[e.from as usize],true,fs,bs)?;out.add(f.index[e.to as usize],false,fr,br)
}
fn direct_energy(s:&Functional64Material,f:&Frontier,v:&LocalVector,e:Contact)->Result<(f64,Interval)>{
    let p=pair(v,f,s,e.from as usize);let q=pair(v,f,s,e.to as usize);let gain=gain(s,e)?;let l=s.anatomy.lambda(e);
    let send=p.send.sin();let receive=q.receive.sin();let residual=receive-gain*send;
    let range=square(Interval::point(receive).sub(Interval::point(gain).mul(Interval::point(send)))).mul(Interval::point(0.5*l));
    Ok((nonnegative(0.5*l*residual*residual)?,valid(range)?))
}
fn baseline_masks(local:usize,n:usize,holes:[u64;2])->Result<([u64;2],[u64;2])>{
    let(r,m)=if n==128{(12,16)}else{(6,8)};let mut band=[0u64;2];let mut residue=[0u64;2];
    for j in local.saturating_sub(r)..(local+r+1).min(n){band[j/64]|=1u64<<(j%64);}
    for j in(local%m..n).step_by(m){if j!=local{residue[j/64]|=1u64<<(j%64);}}
    for word in 0..2{band[word]&=!holes[word];residue[word]&=!holes[word];}
    Ok((band,residue))
}
fn query(tree:&Tree,masks:([u64;2],[u64;2]),count:&mut WorkCount,admission:Admission)->Result<Moment>{
    let a=tree.query(masks.0,count,admission)?;let b=tree.query(masks.1,count,admission)?;a.merge(b,count,admission)
}
fn not_empty(masks:([u64;2],[u64;2]))->bool{masks.0.iter().chain(masks.1.iter()).any(|&x|x!=0)}
pub(super) fn scratch_bytes()->Result<usize>{
    //128 columns/layers, two trees, at most256 summaries/tree; fixed query
    // stack/scratch masks plus full reached force/enclosure arrays.
    let trees=checked_bytes(128*2*256,std::mem::size_of::<Moment>())?;
    let metadata=checked_bytes(128,std::mem::size_of::<Option<PairTrees>>())?;
    let rows=checked_bytes(NODES,std::mem::size_of::<PhasePair>()+2*std::mem::size_of::<Interval>())?;
    // ReceiverStage's actual size includes both aggregate Moments (at most128
    // total). The energy operator additionally owns one incoming accumulator.
    let temporary=add_bytes(add_bytes(std::mem::size_of::<Holes>(),checked_bytes(4*128,8)?)?,std::mem::size_of::<Moment>())?;
    // Above retained masks, construction owns at most one128-summary residue
    // result and one16-summary compact tree. The original recursive query
    // stack remains separately admitted; no caller limit is enlarged.
    let receiver_stage=add_bytes(checked_bytes(64,std::mem::size_of::<ReceiverStage>())?,std::mem::size_of::<Vec<ReceiverStage>>())?;
    [metadata,rows,temporary,receiver_stage,std::mem::size_of::<ColumnAdjacency>(),checked_bytes(192,8)?,checked_bytes(64,std::mem::size_of::<usize>())?,checked_bytes(2,std::mem::size_of::<Option<Moment>>())?,checked_bytes(16,std::mem::size_of::<Moment>())?,checked_bytes(128*2*128,std::mem::size_of::<Moment>())?,checked_bytes(2*NODES,std::mem::size_of::<Contact>())?,checked_bytes(128+16,std::mem::size_of::<Moment>())?].into_iter().try_fold(trees,add_bytes)
}
fn skeleton(s:&Functional64Material,f:&Frontier,count:&mut WorkCount,a:Admission)->Result<Vec<Contact>>{
    let mut edges=Vec::with_capacity(2*f.nodes.len());
    for &node in &f.nodes{count.force(1,a)?;
        for to in Geometry::baseline_intra_neighbors(node).into_iter().flatten(){
            if let Some(e)=s.anatomy.geometry.between(node,to){
                if s.anatomy.geometry.baseline(e)!=0.0&&*s.weights.get(e.authentic_slot as usize)==0.0{edges.push(e);}
            }
        }
    }
    edges.sort_unstable_by_key(|e|e.authentic_slot);Ok(edges)
}
pub(super) fn forces(s:&Functional64Material,f:&Frontier,a:&LocalVector,b:&LocalVector,count:&mut WorkCount,admission:Admission)->Result<Forces>{
    let mut workspace=Workspace::new(s,f,a,b,true,count,admission)?;let mut out=Forces::new(f.nodes.len());
    // Non-inter-layer nodes have only their original ground contribution here.
    for(index,&node)in f.nodes.iter().enumerate(){if layer(node).is_none(){
        stage_receiver(s,f,a,b,index,&mut out,count,admission)?;
    }}
    for group in 0..192{
        let reached=workspace.reached[group];if reached==0{continue;}
        let(kind,local)=if group<128{(0,group)}else{(1,group-128)};let n=width(kind);let offset=if kind==0{32}else{224};
        let mut staged=Vec::with_capacity(reached.count_ones()as usize);let mut indices=[usize::MAX;64];
        let mut columns=reached;let mut others=0u64;
        while columns!=0{let column=columns.trailing_zeros()as usize;columns&=columns-1;
            let node=column*320+offset+local;let index=f.index[node];
            indices[column]=staged.len();staged.push(stage_receiver(s,f,a,b,index,&mut out,count,admission)?);
            let(incoming,outgoing)=workspace.adjacency.row(&s.anatomy.geometry,column,count,admission)?;others|=incoming|outgoing;
        }
        let baseline=g0();
        // New explicit finite order: for each node/role, merge disjoint
        // actual-column Moments in ascending other-column order, then evaluate
        // the same real-law reciprocal force once. All holes are removed first.
        while others!=0{let other=others.trailing_zeros()as usize;others&=others-1;
            let(incoming,outgoing)=workspace.adjacency.row(&s.anatomy.geometry,other,count,admission)?;
            let mut recipients=(incoming|outgoing)&reached;
            let mut common_send=None;let mut common_receive=None;
            while recipients!=0{let column=recipients.trailing_zeros()as usize;recipients&=recipients-1;count.force(1,admission)?;
                let r=&mut staged[indices[column]];
                if outgoing&(1u64<<column)!=0{
                    let holes=r.holes.incoming[other];
                    if holes==[0;2]||not_empty(baseline_masks(local,n,holes)?){
                        let tree=workspace.columns[2*other+kind].as_ref().ok_or(MaterialError::Invalid("missing reached baseline source"))?;
                        let m=if holes==[0;2]{match common_send{Some(m)=>m,None=>{let m=tree.masked(true,local,holes,count,admission)?;common_send=Some(m);m}}}else{tree.masked(true,local,holes,count,admission)?};
                        if m.weight!=0.0{
                            r.incoming_moment=if r.incoming_moment.weight==0.0{m}
                                else{r.incoming_moment.merge(m,count,admission)?};
                        }
                    }
                }
                if incoming&(1u64<<column)!=0{
                    let holes=r.holes.outgoing[other];
                    if holes==[0;2]||not_empty(baseline_masks(local,n,holes)?){
                        let tree=workspace.columns[2*other+kind].as_ref().ok_or(MaterialError::Invalid("missing reached baseline receiver"))?;
                        let m=if holes==[0;2]{match common_receive{Some(m)=>m,None=>{let m=tree.masked(false,local,holes,count,admission)?;common_receive=Some(m);m}}}else{tree.masked(false,local,holes,count,admission)?};
                        if m.weight!=0.0{
                            r.outgoing_moment=if r.outgoing_moment.weight==0.0{m}
                                else{r.outgoing_moment.merge(m,count,admission)?};
                        }
                    }
                }
            }
        }
        for r in staged{
            let(index,node,v,u,ds,dr)=(r.index,r.node,r.v,r.u,r.ds,r.dr);
            let m=r.incoming_moment;
            if m.weight!=0.0{count.force(1,admission)?;
                let l=LAMBDA/s.anatomy.geometry.degree(node)as f64;
                let value=l*m.weight*(u-baseline*m.mean)*dr;
                let range=Interval::point(l).mul(m.w.mul(Interval::point(u)).sub(Interval::point(baseline).mul(m.s))).mul(Interval::point(dr));out.add(index,false,value,range)?;
            }
            let m=r.outgoing_moment;
            if m.weight!=0.0{count.force(1,admission)?;
                let value=-baseline*m.weight*(m.mean-baseline*v)*ds;
                let range=Interval::point(-baseline).mul(m.s.sub(Interval::point(baseline).mul(Interval::point(v)).mul(m.w))).mul(Interval::point(ds));out.add(index,true,value,range)?;
            }
        }
    }
    for e in skeleton(s,f,count,admission)?{direct_force(s,f,a,b,e,&mut out,count,admission)?;}
    for edge in &f.edges{if *s.weights.get(edge.contact.authentic_slot as usize)!=0.0{direct_force(s,f,a,b,edge.contact,&mut out,count,admission)?;}}
    Ok(out)
}
pub(super) fn energy(s:&Functional64Material,f:&Frontier,v:&LocalVector,new_contacts:&[(usize,f64)],count:&mut WorkCount,admission:Admission)->Result<Energy>{
    let mut workspace=Workspace::new(s,f,v,v,false,count,admission)?;let mut out=Energy::zero();
    for(index,&node)in f.nodes.iter().enumerate(){let holes=Holes::new(s,node,count,admission)?;let u=v.nodes[index].receive.sin();
        let zero=s.anatomy.geometry.baseline_zero_incoming_count(node).checked_sub(holes.zero_incoming).ok_or(MaterialError::Invalid("negative baseline ground count"))?;
        if zero>0{count.force(1,admission)?;let l=LAMBDA/s.anatomy.geometry.degree(node)as f64;let factor=0.5*l*zero as f64;
            out.add(factor*u*u,Interval::point(0.5*l).mul(Interval::point(zero as f64)).mul(square(Interval::point(u))))?;}
        let Some((kind,_,local))=layer(node)else{continue;};let n=width(kind);let column=node/320;let baseline=g0();
        let(mut others,_)=workspace.adjacency.row(&s.anatomy.geometry,column,count,admission)?;
        let mut incoming=Moment::empty();
        while others!=0{let other=others.trailing_zeros()as usize;others&=others-1;count.force(1,admission)?;
            if holes.incoming[other]!=[0;2]&&!not_empty(baseline_masks(local,n,holes.incoming[other])?){continue;}
            let tree=workspace.columns[2*other+kind].as_ref().ok_or(MaterialError::Invalid("missing reached baseline energy source"))?;
            let m=tree.masked(true,local,holes.incoming[other],count,admission)?;
            if m.weight!=0.0{
                incoming=if incoming.weight==0.0{m}else{incoming.merge(m,count,admission)?};
            }
        }
        if incoming.weight!=0.0{count.force(1,admission)?;
            let m=incoming;let l=LAMBDA/s.anatomy.geometry.degree(node)as f64;let difference=u-baseline*m.mean;
            let value=0.5*l*(m.weight*difference*difference+baseline*baseline*m.m2);
            let range=m.w.mul(square(Interval::point(u))).sub(Interval::point(2.0*baseline).mul(Interval::point(u)).mul(m.s))
                .add(Interval::point(baseline).mul(Interval::point(baseline)).mul(m.s2)).mul(Interval::point(0.5*l));out.add(value,range)?;
        }
    }
    for e in skeleton(s,f,count,admission)?{count.force(1,admission)?;let(value,range)=direct_energy(s,f,v,e)?;out.add(value,range)?;}
    for edge in &f.edges{if *s.weights.get(edge.contact.authentic_slot as usize)!=0.0{count.force(1,admission)?;let(value,range)=direct_energy(s,f,v,edge.contact)?;out.add(value,range)?;}}
    for &(slot,_)in new_contacts{if f.edges.binary_search_by_key(&(slot as u32),|e|e.contact.authentic_slot).is_err()&&*s.weights.get(slot)!=0.0{
        count.force(1,admission)?;let(value,range)=direct_energy(s,f,v,s.anatomy.contact(slot)?)?;out.add(value,range)?;
    }}Ok(out)
}
pub(super) fn error(value:f64,bound:Interval)->Result<f64>{discrepancy(value,bound)}

#[cfg(test)]
mod reuse_tests{
    use super::*;
    // Exact49d90747 predecessor query, retained only as a bitwise reference.
    impl Tree{
    fn predecessor_query(&self,bits:[u64;2],count:&mut WorkCount,admission:Admission)->Result<Moment>{
        fn walk(tree:&Tree,index:usize,lo:usize,width:usize,bits:[u64;2],count:&mut WorkCount,a:Admission)->Result<Moment>{
            count.force(1,a)?;
            let mut occupied=0usize;
            for word in 0..2{let left=lo.max(word*64);let right=(lo+width).min((word+1)*64);
                if left<right{let length=right-left;let mask=if length==64{u64::MAX}else{((1u64<<length)-1)<<(left%64)};occupied+=(bits[word]&mask).count_ones()as usize;}}
            if occupied==0{return Ok(Moment::empty());}if occupied==width{return Ok(tree.nodes[index]);}
            if width==1{return Err(MaterialError::Invalid("contact mask leaf"));}
            let left=walk(tree,index*2,lo,width/2,bits,count,a)?;
            let right=walk(tree,index*2+1,lo+width/2,width/2,bits,count,a)?;
            left.merge(right,count,a)
        }
        walk(self,1,0,self.width,bits,count,admission)
    }
    }
    fn predecessor_masked(tree:&Tree,masks:([u64;2],[u64;2]),count:&mut WorkCount,a:Admission)->Result<Moment>{
        let left=tree.predecessor_query(masks.0,count,a)?;let right=tree.predecessor_query(masks.1,count,a)?;left.merge(right,count,a)
    }
    fn admission()->Admission{Admission{max_force_terms:50_000_000,max_yield_queries:10_000_000,
        max_staged_bytes:scratch_bytes().unwrap(),max_source_bytes:1<<20}}
    fn bits(m:Moment)->[u64;9]{[m.weight,m.mean,m.m2,m.w.lo,m.w.hi,m.s.lo,m.s.hi,m.s2.lo,m.s2.hi].map(f64::to_bits)}
    fn operator_terms(m:Moment)->[u64;3]{
        // Fixed signed operand fixture for the unchanged incoming/outgoing DG
        // and positive energy expressions, not a new material coefficient.
        let(u,v,ds,dr)=(-0.125,0.375,0.75,0.875);let b=g0();let l=LAMBDA/1024.0;let z=u-b*m.mean;
        [l*m.weight*z*dr,-b*m.weight*(m.mean-b*v)*ds,0.5*l*(m.weight*z*z+b*b*m.m2)].map(f64::to_bits)
    }
    #[test]
    fn compact_congruence_queries_preserve_every_summary_and_operator_bit(){
        let a=admission();
        for n in [64usize,128]{for weighted in [false,true]{
            let values=(0..n).map(|i|match i%7{0=>-0.0,1=>0.0,_=>(i as f64-n as f64/2.0)/n as f64}).collect::<Vec<_>>();
            let weights=(0..n).map(|i|if weighted{LAMBDA/(i+1)as f64}else{1.0}).collect::<Vec<_>>();
            let mut construction=WorkCount::default();let tree=Tree::new(&values,&weights,&mut construction,a).unwrap();
            let mut compact_work=WorkCount::default();let actual=tree.baseline_summaries(&mut compact_work,a).unwrap();
            let mut prior_work=WorkCount::default();
            for local in 0..n{let masks=baseline_masks(local,n,[0;2]).unwrap();let prior=predecessor_masked(&tree,masks,&mut prior_work,a).unwrap();
                assert_eq!(bits(actual[local]),bits(prior));assert_eq!(operator_terms(actual[local]),operator_terms(prior));
            }
            assert!(compact_work.force_terms<prior_work.force_terms);
            // The residue alone is the exact former sparse masked query,
            // including removal of self before its later union with the band.
            let mut count=WorkCount::default();let residues=tree.residue_without_self(&mut count,a).unwrap();
            for local in 0..n{let masks=baseline_masks(local,n,[0;2]).unwrap();
                assert_eq!(bits(residues[local]),bits(tree.predecessor_query(masks.1,&mut count,a).unwrap()));
            }
            let mut paired_work=WorkCount::default();let paired=PairTrees::new(tree.clone(),Some(tree.clone()),&mut paired_work,a).unwrap();
            let mut energy_work=WorkCount::default();let energy=PairTrees::new(tree.clone(),None,&mut energy_work,a).unwrap();
            assert!(energy.receive.is_none());assert!(energy_work.force_terms<paired_work.force_terms);
            for local in 0..n{
                let mut self_hole=[0;2];self_hole[local/64]=1u64<<(local%64);
                let mut congruent_hole=[0;2];let j=(local+if n==128{16}else{8})%n;congruent_hole[j/64]=1u64<<(j%64);
                for holes in [[0;2],self_hole,congruent_hole,[u64::MAX;2]]{
                    let prior=predecessor_masked(&tree,baseline_masks(local,n,holes).unwrap(),&mut count,a).unwrap();
                    let send=paired.masked(true,local,holes,&mut count,a).unwrap();
                    let receive=paired.masked(false,local,holes,&mut count,a).unwrap();
                    let scalar_energy=energy.masked(true,local,holes,&mut count,a).unwrap();
                    for current in [send,receive,scalar_energy]{assert_eq!(bits(current),bits(prior));assert_eq!(operator_terms(current),operator_terms(prior));}
                }
            }
        }}
        // Direct query coverage includes the compact8-site residue subtree,
        // empty/full/single-bit masks and arbitrary holes, with signed and
        // entirely zero values. Both selected and outward-summary bits matter.
        for n in [8usize,64,128]{for zero_values in [false,true]{for weighted in [false,true]{
            let values=(0..n).map(|i|if zero_values{0.0}else{match i%7{0=>-0.0,1=>0.0,_=>(i as f64-n as f64/2.0)/n as f64}}).collect::<Vec<_>>();
            let weights=(0..n).map(|i|if weighted{LAMBDA/(i+1)as f64}else{1.0}).collect::<Vec<_>>();
            let mut build=WorkCount::default();
            let tree=if n==8{
                let mut nodes=vec![Moment::empty();16];
                for i in 0..8{nodes[8+i]=Moment::leaf(values[i],weights[i]).unwrap();}
                for i in(1..8).rev(){nodes[i]=nodes[2*i].merge(nodes[2*i+1],&mut build,a).unwrap();}
                Tree{width:8,nodes}
            }else{Tree::new(&values,&weights,&mut build,a).unwrap()};
            let mut masks=vec![[0;2],[u64::MAX;2],[0xa55a_0123_f00f_8001,0x0101_aaaa_5555_8080]];
            for local in 0..n{let mut single=[0;2];single[local/64]=1u64<<(local%64);masks.push(single);}
            if n==8{for mask in 0..256{masks.push([mask,0]);}}
            else{for local in 0..n{
                for holes in [[0;2],[0xa55a_0123_f00f_8001,0x0101_aaaa_5555_8080]]{
                    let(band,residue)=baseline_masks(local,n,holes).unwrap();masks.push(band);masks.push(residue);
                }
            }}
            for mask in masks{
                let mut original_work=WorkCount::default();let prior=tree.predecessor_query(mask,&mut original_work,a).unwrap();
                let mut current_work=WorkCount::default();let current=tree.query(mask,&mut current_work,a).unwrap();
                assert_eq!(bits(current),bits(prior));assert_eq!(operator_terms(current),operator_terms(prior));
                assert!(current_work.force_terms<=original_work.force_terms);
            }
            let mut original_work=WorkCount::default();tree.predecessor_query([1,0],&mut original_work,a).unwrap();
            let mut current_work=WorkCount::default();tree.query([1,0],&mut current_work,a).unwrap();
            assert!(current_work.force_terms<original_work.force_terms);
        }}}
    }
}
