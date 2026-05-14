import os
import requests
from dotenv import load_dotenv

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")

# Highway graph — nodes are cities, edges are (city1, city2, distance_km, highway)
HIGHWAY_GRAPH = {
    "Delhi":          [("Nagpur", 1090, "NH-44"), ("Mumbai", 1400, "NH-48")],
    "Nagpur":         [("Delhi", 1090, "NH-44"), ("Hyderabad", 500, "NH-44")],
    "Hyderabad":      [("Nagpur", 500, "NH-44"), ("Bangalore", 570, "NH-44"),
                       ("Kurnool", 210, "NH-65"), ("Vijayawada", 270, "NH-16")],
    "Bangalore":      [("Hyderabad", 570, "NH-44"), ("Chennai", 350, "NH-44"),
                       ("Krishnagiri", 90, "NH-44"), ("Mysore", 145, "NH-275"),
                       ("Hubli", 410, "NH-48")],
    "Chennai":        [("Bangalore", 350, "NH-44"), ("Krishnagiri", 260, "NH-44"),
                       ("Nellore", 175, "NH-16")],
    "Krishnagiri":    [("Bangalore", 90, "NH-44"), ("Chennai", 260, "NH-44")],
    "Mumbai":         [("Delhi", 1400, "NH-48"), ("Pune", 150, "NH-48")],
    "Pune":           [("Mumbai", 150, "NH-48"), ("Hubli", 480, "NH-48"),
                       ("Solapur", 250, "NH-65")],
    "Hubli":          [("Pune", 480, "NH-48"), ("Bangalore", 410, "NH-48")],
    "Vijayawada":     [("Hyderabad", 270, "NH-16"), ("Nellore", 290, "NH-16"),
                       ("Visakhapatnam", 350, "NH-16")],
    "Visakhapatnam":  [("Vijayawada", 350, "NH-16")],
    "Nellore":        [("Chennai", 175, "NH-16"), ("Vijayawada", 290, "NH-16")],
    "Mysore":         [("Bangalore", 145, "NH-275"), ("Coimbatore", 210, "NH-275")],
    "Coimbatore":     [("Mysore", 210, "NH-275"), ("Kochi", 190, "NH-275")],
    "Kochi":          [("Coimbatore", 190, "NH-275")],
    "Kurnool":        [("Hyderabad", 210, "NH-65"), ("Solapur", 480, "NH-65")],
    "Solapur":        [("Kurnool", 480, "NH-65"), ("Pune", 250, "NH-65")],
}

def get_risk_scores():
    import sqlite3
    conn = sqlite3.connect("data/freight_risk.db")
    cursor = conn.cursor()
    cursor.execute("SELECT highway, risk_score FROM highway_predictions")
    scores = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return scores

def dijkstra(origin, destination, risk_scores):
    import heapq

    # Cost = distance * risk_weight
    # risk_weight: LOW=1.0, MEDIUM=1.5, HIGH=2.5
    def risk_weight(highway):
        score = risk_scores.get(highway, 25.0)
        if score >= 60:
            return 2.5
        elif score >= 35:
            return 1.5
        return 1.0

    queue = [(0, origin, [], [])]
    visited = set()

    while queue:
        cost, node, path, highways_used = heapq.heappop(queue)

        if node in visited:
            continue
        visited.add(node)

        path = path + [node]

        if node == destination:
            return {
                "path": path,
                "highways": list(dict.fromkeys(highways_used)),
                "total_cost": round(cost, 2),
                "found": True
            }

        for neighbor, distance, highway in HIGHWAY_GRAPH.get(node, []):
            if neighbor not in visited:
                weight = distance * risk_weight(highway)
                heapq.heappush(
                    queue,
                    (cost + weight, neighbor, path, highways_used + [highway])
                )

    return {"path": [], "highways": [], "total_cost": 0, "found": False}


def get_route_distance(origin, destination):
    try:
        cities_coords = {
            "Delhi": [77.2090, 28.6139],
            "Nagpur": [79.0882, 21.1458],
            "Hyderabad": [78.4867, 17.3850],
            "Bangalore": [77.5946, 12.9716],
            "Chennai": [80.2707, 13.0827],
            "Krishnagiri": [78.2137, 12.5186],
            "Mumbai": [72.8777, 19.0760],
            "Pune": [73.8567, 18.5204],
            "Hubli": [75.1240, 15.3647],
            "Vijayawada": [80.6480, 16.5062],
            "Visakhapatnam": [83.2185, 17.6868],
            "Nellore": [79.9865, 14.4426],
            "Mysore": [76.6394, 12.2958],
            "Coimbatore": [76.9558, 11.0168],
            "Kochi": [76.2673, 9.9312],
            "Kurnool": [78.0373, 15.8281],
            "Solapur": [75.9064, 17.6599],
        }

        if origin not in cities_coords or destination not in cities_coords:
            return None

        body = {
            "coordinates": [
                cities_coords[origin],
                cities_coords[destination]
            ]
        }
        headers = {
            "Authorization": ORS_API_KEY,
            "Content-Type": "application/json"
        }
        res = requests.post(
            "https://api.openrouteservice.org/v2/directions/driving-car/json",
            json=body,
            headers=headers,
            timeout=10
        )
        data = res.json()
        route = data["routes"][0]["summary"]
        return {
            "distance_km": round(route["distance"] / 1000, 1),
            "duration_hours": round(route["duration"] / 3600, 1)
        }
    except Exception as e:
        print(f"ORS error: {e}")
        return None


def recommend_route(origin, destination):
    risk_scores = get_risk_scores()
    result = dijkstra(origin, destination, risk_scores)

    if not result["found"]:
        return {
            "origin": origin,
            "destination": destination,
            "found": False,
            "message": f"No route found between {origin} and {destination}"
        }

    highways = result["highways"]
    primary_highway = highways[0] if highways else "Unknown"
    risk_score = risk_scores.get(primary_highway, 25.0)
    risk_level = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 35 else "LOW"

    ors_data = get_route_distance(origin, destination)

    return {
        "origin": origin,
        "destination": destination,
        "found": True,
        "path": result["path"],
        "highways": highways,
        "primary_highway": primary_highway,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "distance_km": ors_data["distance_km"] if ors_data else None,
        "duration_hours": ors_data["duration_hours"] if ors_data else None,
        "recommendation": (
            "Avoid this route - high disruption risk" if risk_level == "HIGH"
            else "Use with caution - monitor conditions" if risk_level == "MEDIUM"
            else "Safe to proceed"
        )
    }

def recommend_route_with_alternate(origin, destination):
    risk_scores = get_risk_scores()

    # Route A - normal Dijkstra
    route_a = dijkstra(origin, destination, risk_scores)

    # Route B - remove Route A primary highway from graph
    if route_a["found"] and route_a["highways"]:
        primary_highway = route_a["highways"][0]
        # Build modified risk scores with primary highway heavily penalized
        modified_scores = dict(risk_scores)
        modified_scores[primary_highway] = 999
        route_b = dijkstra(origin, destination, modified_scores)
    else:
        route_b = {"found": False}

    # Get ORS distances for both
    ors_a = get_route_distance(origin, destination)

    # Build response
    result = {
        "origin": origin,
        "destination": destination,
        "primary_route": None,
        "alternate_route": None,
        "recommendation": ""
    }

    if route_a["found"]:
        hw_a = route_a["highways"][0] if route_a["highways"] else "Unknown"
        score_a = risk_scores.get(hw_a, 0)
        result["primary_route"] = {
            "path": route_a["path"],
            "highways": route_a["highways"],
            "primary_highway": hw_a,
            "risk_score": score_a,
            "risk_level": "HIGH" if score_a >= 60 else "MEDIUM" if score_a >= 35 else "LOW",
            "distance_km": ors_a["distance_km"] if ors_a else None,
            "duration_hours": ors_a["duration_hours"] if ors_a else None,
            "recommendation": (
                "Avoid - high disruption risk" if score_a >= 60
                else "Use with caution" if score_a >= 35
                else "Safe to proceed"
            )
        }

    if route_b.get("found"):
        hw_b = route_b["highways"][0] if route_b["highways"] else "Unknown"
        # Use modified score not 999
        score_b = risk_scores.get(hw_b, 0)
        ors_b = get_route_distance(
            route_b["path"][0],
            route_b["path"][-1]
        )
        result["alternate_route"] = {
            "path": route_b["path"],
            "highways": route_b["highways"],
            "primary_highway": hw_b,
            "risk_score": score_b,
            "risk_level": "HIGH" if score_b >= 60 else "MEDIUM" if score_b >= 35 else "LOW",
            "distance_km": ors_b["distance_km"] if ors_b else None,
            "duration_hours": ors_b["duration_hours"] if ors_b else None,
            "recommendation": (
                "Avoid - high disruption risk" if score_b >= 60
                else "Use with caution" if score_b >= 35
                else "Safe to proceed"
            )
        }

    # Overall recommendation
    if result["primary_route"] and result["alternate_route"]:
        pr = result["primary_route"]
        ar = result["alternate_route"]
        if pr["risk_level"] == "LOW" and ar["risk_level"] == "LOW":
            result["recommendation"] = (
                f"Both routes are safe. "
                f"Route A via {pr['primary_highway']} is faster "
                f"({pr['duration_hours']}hrs). "
                f"Route B via {ar['primary_highway']} is "
                f"{'shorter' if (ar['distance_km'] or 0) < (pr['distance_km'] or 0) else 'longer'} "
                f"({ar['duration_hours']}hrs)."
            )
        elif pr["risk_level"] in ["HIGH", "MEDIUM"]:
            result["recommendation"] = (
                f"Route A via {pr['primary_highway']} has {pr['risk_level']} risk. "
                f"Recommend Route B via {ar['primary_highway']} instead."
            )
        else:
            result["recommendation"] = (
                f"Route A via {pr['primary_highway']} is safest. "
                f"Use Route B via {ar['primary_highway']} as backup."
            )
    elif result["primary_route"]:
        result["recommendation"] = (
            f"Only one route found via {result['primary_route']['primary_highway']}."
        )

    return result

if __name__ == "__main__":
    import json
    print("Testing alternate route recommendation...")
    result = recommend_route_with_alternate("Delhi", "Chennai")
    print(json.dumps(result, indent=2))
    print("\n---\n")
    result2 = recommend_route_with_alternate("Hyderabad", "Kochi")
    print(json.dumps(result2, indent=2))