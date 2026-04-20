(* ::Package:: *)

(* latency-model.wl
   Symbolic reproducible model of long-haul latency over
   standard fibre, hollow-core fibre, and Starlink LEO.

   Run with free Wolfram Engine:
     wolframscript -file latency-model.wl
*)

(* ---- constants ---- *)
cKms     = 299792.458;                    (* km/s *)
nSMF     = 1.468;                          (* G.652 group index *)
vSMF     = cKms/nSMF;                      (* ~204218 km/s *)
vHCF     = 0.997 cKms;                     (* Microsoft/Lumenisity NANF *)
REarth   = 6371.0;
hLEO     = 550.0;
tSatProc = 1.0;  (* ms *)
tGSProc  = 2.0;  (* ms *)
tRouter  = 0.05; (* ms *)
nHops    = 8;

(* ---- geometry ---- *)
greatCircle[{\[Phi]1_,\[Lambda]1_},{\[Phi]2_,\[Lambda]2_}] :=
  2 REarth ArcSin[ Sqrt[ Sin[(\[Phi]2-\[Phi]1)/2]^2 +
                         Cos[\[Phi]1] Cos[\[Phi]2] Sin[(\[Lambda]2-\[Lambda]1)/2]^2 ] ];

deg[x_] := x Degree;

cities = <|
  "London"   -> {deg[51.5074], deg[-0.1278]},
  "NewYork"  -> {deg[40.7128], deg[-74.0060]},
  "Sydney"   -> {deg[-33.8688], deg[151.2093]}
|>;

gc[a_,b_] := greatCircle[cities[a], cities[b]];

cableKm = <|
  {"London","NewYork"} -> 6200.0,
  {"London","Sydney"}  -> 22000.0
|>;

(* ---- latency formulas ---- *)
fibreOneWay[dCable_, v_] := dCable/v * 1000 + nHops * tRouter;   (* ms *)

leoArc[dGC_] := dGC (REarth + hLEO)/REarth;

starlinkIdeal[dGC_] :=
  Module[{arc = leoArc[dGC], nIsl},
    nIsl = Max[1, Round[arc/2000]];
    (arc + 2 hLEO)/cKms * 1000 + nIsl * tSatProc + 2 tGSProc
  ];

starlinkRealistic[dGC_, backhaulKm_] :=
  Module[{leoAccess = 2 (leoArc[500] + hLEO)},
    leoAccess/cKms * 1000 + backhaulKm/vSMF * 1000 +
      2 tSatProc + 4 tGSProc + nHops tRouter
  ];

(* ---- build table ---- *)
routes = Keys[cableKm];
results = Flatten[ Table[
  {a, b} = r;
  dCable = cableKm[r];
  dGC    = gc[a, b];
  {
    <| "route"->a<>" <-> "<>b, "tech"->"SMF fibre",          "rtt_ms"-> 2 fibreOneWay[dCable, vSMF] |>,
    <| "route"->a<>" <-> "<>b, "tech"->"Hollow-core (NANF)", "rtt_ms"-> 2 fibreOneWay[dCable, vHCF] |>,
    <| "route"->a<>" <-> "<>b, "tech"->"Starlink (ideal)",   "rtt_ms"-> 2 starlinkIdeal[dGC] |>,
    <| "route"->a<>" <-> "<>b, "tech"->"Starlink (realistic)",
       "rtt_ms"-> 2 starlinkRealistic[dGC, If[MatchQ[r,{"London","Sydney"}], 20000, 5000]] |>
  }, {r, routes}], 1];

Print[Grid[Prepend[
  {#route, #tech, NumberForm[#rtt_ms, {5,1}]} & /@ results,
  {"Route","Technology","RTT (ms)"}], Alignment->Left, Frame->All, Spacings->{2,1}]];

(* Sensitivity: RTT of HCF transatlantic vs refractive index assumption *)
Print["\nSensitivity \[Dash] LON<->NYC as a function of medium speed (fraction of c):"];
Print[TableForm[
  Table[{ToString[Round[100 f]]<>"%", NumberForm[2 fibreOneWay[6200, f cKms], {5,1}]<>" ms"},
    {f, {0.67, 0.80, 0.90, 0.997}}]]];
