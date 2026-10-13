"""Generate a reproducible SUMO grid, normal demand, and one ambulance route."""
import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def run(cmd, env=None):
    print("+", " ".join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True, env=env)


def add_ambulance(route_file, seed, depart=15):
    tree = ET.parse(route_file)
    root = tree.getroot()
    candidates = []
    for vehicle in root.findall("vehicle"):
        route = vehicle.find("route")
        if route is not None and route.get("edges"):
            edges = route.get("edges", "").split()
            if len(edges) >= 2:
                candidates.append((len(edges), edges))
    if not candidates:
        raise SystemExit(
            "Could not find a resolved vehicle route in the generated route file. "
            "Inspect the randomTrips/duarouter output before adding ambulance demand."
        )
    # Deterministic: choose the longest resolved route, then clone its edge sequence.
    edges = max(candidates, key=lambda item: item[0])[1]
    vtype = ET.Element("vType", {
        "id": "emergency", "vClass": "emergency", "accel": "3.0",
        "decel": "6.0", "sigma": "0.0", "length": "5.0",
        "maxSpeed": "16.67", "speedFactor": "1.0", "color": "1,0,0",
    })
    # SUMO expects vehicle types to be defined before vehicles that use them.
    root.insert(0, vtype)
    ambulance = ET.SubElement(root, "vehicle", {
        "id": f"ambulance_seed{seed}", "type": "emergency",
        "depart": str(float(depart)), "departLane": "best",
        "departSpeed": "max",
    })
    ET.SubElement(ambulance, "route", {"edges": " ".join(edges)})
    ET.indent(tree, space="  ")
    tree.write(route_file, encoding="UTF-8", xml_declaration=True)
    print(f"Added ambulance_seed{seed} at t={depart}s using {len(edges)} route edges.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--end", type=int, default=1800)
    parser.add_argument("--out", default="data/demo")
    parser.add_argument("--ambulance-depart", type=int, default=15)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    net, rou, cfg = out / "demo.net.xml", out / "demo.rou.xml", out / "demo.sumocfg"
    run([
        "netgenerate", "--grid", "--grid.number", "3", "--grid.length", "250",
        "--grid.attach-length", "100", "--tls.guess", "--tls.guess.threshold", "1",
        "--default.speed", "13.89", "--output-file", net,
    ])
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        raise SystemExit("Set SUMO_HOME to your SUMO installation directory first.")
    trips_tool = Path(sumo_home) / "tools" / "randomTrips.py"
    if not trips_tool.exists():
        raise SystemExit(f"Cannot find {trips_tool}. Correct SUMO_HOME.")
    run([
        sys.executable, trips_tool, "-n", net, "-r", rou,
        "--seed", args.seed, "--period", "2.0", "--end", args.end,
        "--binomial", "4", "--validate",
    ])
    add_ambulance(rou, args.seed, args.ambulance_depart)
    cfg.write_text(
        f"""<configuration>
  <input><net-file value="{net.name}"/><route-files value="{rou.name}"/></input>
  <time><begin value="0"/><end value="{args.end}"/><step-length value="1"/></time>
  <processing><time-to-teleport value="-1"/></processing>
</configuration>
""", encoding="utf-8")
    print(f"Demo scenario created at {out.resolve()}")


if __name__ == "__main__":
    main()
