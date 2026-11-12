from math import radians, sin, cos, asin, sqrt
from ortools.graph.python import min_cost_flow

PENALTY = 10_000  # cost of leaving a need unmet / surplus unused; forces real transfers first


def haversine_km(lat1, lng1, lat2, lng2):
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lng2 - lng1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _solve_group(rows, resource_type, category):
    """Minimum-Cost Flow for one resource category. Cost = straight-line km."""
    sup = [r for r in rows if r["balance"] > 0]
    dem = [r for r in rows if r["balance"] < 0]
    if not sup or not dem:
        return [], []
    total_s = sum(int(round(r["balance"])) for r in sup)
    total_d = sum(int(round(-r["balance"])) for r in dem)
    nodes = sup + dem
    dummy = len(nodes)
    smcf = min_cost_flow.SimpleMinCostFlow()
    for i, r in enumerate(nodes):
        q = int(round(abs(r["balance"])))
        smcf.set_node_supply(i, q if r["balance"] > 0 else -q)
    # dummy node balances the network when total supply != total demand
    smcf.set_node_supply(dummy, total_d - total_s)
    arcs = []
    for i, s in enumerate(sup):
        for j, d in enumerate(dem, start=len(sup)):
            km = haversine_km(s["lat"], s["lng"], d["lat"], d["lng"])
            smcf.add_arc_with_capacity_and_unit_cost(i, j, max(total_s, total_d), int(round(km)))
            arcs.append((i, j, km))
    for i in range(len(sup)):
        smcf.add_arc_with_capacity_and_unit_cost(i, dummy, total_s, PENALTY)
    for j in range(len(sup), len(nodes)):
        smcf.add_arc_with_capacity_and_unit_cost(dummy, j, total_d, PENALTY)
    if smcf.solve() != smcf.OPTIMAL:
        return [], []
    transfers, unmet = [], []
    n_real = len(arcs)
    for a in range(smcf.num_arcs()):
        flow = smcf.flow(a)
        if flow <= 0:
            continue
        t, h = smcf.tail(a), smcf.head(a)
        if a < n_real:
            i, j, km = arcs[a]
            s, d = nodes[i], nodes[j]
            transfers.append({
                "from": s["location"], "to": d["location"],
                "from_lat": float(s["lat"]), "from_lng": float(s["lng"]),
                "to_lat": float(d["lat"]), "to_lng": float(d["lng"]),
                "quantity": int(flow), "unit": s["unit"], "category": category,
                "resource_type": resource_type, "distance_km": round(km),
                "effort": int(flow * round(km)),
            })
        elif h != dummy and t == dummy:
            unmet.append({"location": nodes[h]["location"], "quantity": int(flow),
                          "unit": nodes[h]["unit"], "category": category})
    return transfers, unmet


def recommend_transfers(df, resource_type):
    """Returns (transfers, unmet_needs) for one resource type, per category."""
    transfers, unmet = [], []
    d = df[df["resource_type"] == resource_type]
    for category, g in d.groupby("category"):
        t, u = _solve_group(g.to_dict("records"), resource_type, category)
        transfers += t
        unmet += u
    return transfers, unmet
