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


if __name__ == "__main__":
    print("Testing Dijkstra router...")
    result = recommend_route("Delhi", "Chennai")
    print(result)
    result2 = recommend_route("Hyderabad", "Kochi")
    print(result2)