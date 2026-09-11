// Offline read-only projection of a saved diagnostic receipt; never runtime.
const fs=require("fs");const r=JSON.parse(fs.readFileSync(process.argv[2]));
const hubs=r.intervals[0].association_neighborhoods;
const result=hubs.map(h=>{
 const hub=h.association, allowed=new Set(h.mounted_lineages), integration=new Set();
 for(const i of r.intervals)for(const [a,b]of i.raw_causal_bonds_before_selection){if(a===hub&&allowed.has(b))integration.add(b);if(b===hub&&allowed.has(a))integration.add(a)}
 if(integration.size!==h.association_l6_contacts)throw Error("Incomplete mounted integration census");
 const earlier=new Set();
 return {hub,integration_count:integration.size,clocks:r.intervals.map(i=>{
 const edges=i.raw_causal_bonds_before_selection.filter(([a,b])=>allowed.has(a)&&allowed.has(b)&&((a===hub&&integration.has(b))||(b===hub&&integration.has(a))||(integration.has(a)&&!integration.has(b)&&b!==hub)||(integration.has(b)&&!integration.has(a)&&a!==hub)));
 const reached=new Set([hub]);let changed=true;while(changed){changed=false;for(const[a,b]of edges){if(reached.has(a)&&!reached.has(b)){reached.add(b);changed=true}if(reached.has(b)&&!reached.has(a)){reached.add(a);changed=true}}}
 const row={clock:i.clock,raw_bonds:i.raw_causal_bonds_before_selection.length,own_causal_bonds:edges.length,hub_connected_bonds:edges.filter(([a,b])=>reached.has(a)&&reached.has(b)).length,emitted_in_neighborhood:i.emitted_lineages.filter(x=>allowed.has(x)),emitted_in_hub_component:i.emitted_lineages.filter(x=>reached.has(x)),earlier_emitted_in_hub_component:[...earlier].filter(x=>reached.has(x))};
 i.emitted_lineages.forEach(x=>earlier.add(x));return row;
 })};
});
process.stdout.write(JSON.stringify({exact:r.existing_continuation_successor_exact,results:result},null,2));
