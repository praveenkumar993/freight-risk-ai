# NHAI Toll rates (₹ per trip for standard truck/HCV)
# Source: NHAI published toll plaza rates 2024-25

TOLL_PLAZAS = {
    # NH-44
    ("Delhi",        "Nagpur"):        {"plazas": 8,  "toll": 1840, "highway": "NH-44"},
    ("Nagpur",       "Hyderabad"):     {"plazas": 5,  "toll": 1150, "highway": "NH-44"},
    ("Hyderabad",    "Bangalore"):     {"plazas": 6,  "toll": 1380, "highway": "NH-44"},
    ("Bangalore",    "Krishnagiri"):   {"plazas": 2,  "toll": 460,  "highway": "NH-44"},
    ("Krishnagiri",  "Chennai"):       {"plazas": 3,  "toll": 690,  "highway": "NH-44"},
    # NH-48
    ("Mumbai",       "Pune"):          {"plazas": 3,  "toll": 690,  "highway": "NH-48"},
    ("Pune",         "Hubli"):         {"plazas": 6,  "toll": 1380, "highway": "NH-48"},
    ("Hubli",        "Bangalore"):     {"plazas": 5,  "toll": 1150, "highway": "NH-48"},
    # NH-16
    ("Chennai",      "Nellore"):       {"plazas": 3,  "toll": 690,  "highway": "NH-16"},
    ("Nellore",      "Guntur"):        {"plazas": 2,  "toll": 460,  "highway": "NH-16"},
    ("Guntur",       "Vijayawada"):    {"plazas": 1,  "toll": 230,  "highway": "NH-16"},
    ("Vijayawada",   "Rajahmundry"):   {"plazas": 3,  "toll": 690,  "highway": "NH-16"},
    ("Rajahmundry",  "Kakinada"):      {"plazas": 1,  "toll": 230,  "highway": "NH-16"},
    ("Kakinada",     "Visakhapatnam"): {"plazas": 3,  "toll": 690,  "highway": "NH-16"},
    # NH-275
    ("Bangalore",    "Mysore"):        {"plazas": 3,  "toll": 690,  "highway": "NH-275"},
    ("Mysore",       "Coimbatore"):    {"plazas": 4,  "toll": 920,  "highway": "NH-275"},
    ("Coimbatore",   "Thrissur"):      {"plazas": 3,  "toll": 690,  "highway": "NH-275"},
    ("Thrissur",     "Kochi"):         {"plazas": 2,  "toll": 460,  "highway": "NH-275"},
    ("Kochi",        "Kozhikode"):     {"plazas": 4,  "toll": 920,  "highway": "NH-275"},
    ("Kozhikode",    "Thiruvananthapuram"): {"plazas": 6, "toll": 1380, "highway": "NH-275"},
    # NH-65
    ("Hyderabad",    "Kurnool"):       {"plazas": 3,  "toll": 690,  "highway": "NH-65"},
    ("Kurnool",      "Solapur"):       {"plazas": 6,  "toll": 1380, "highway": "NH-65"},
    ("Solapur",      "Pune"):          {"plazas": 3,  "toll": 690,  "highway": "NH-65"},
    ("Hyderabad",    "Warangal"):      {"plazas": 2,  "toll": 460,  "highway": "NH-65"},
    # NH-544
    ("Chennai",      "Vellore"):       {"plazas": 2,  "toll": 460,  "highway": "NH-544"},
    ("Vellore",      "Salem"):         {"plazas": 3,  "toll": 690,  "highway": "NH-544"},
    ("Salem",        "Tiruchirappalli"):{"plazas": 3, "toll": 690,  "highway": "NH-544"},
    ("Tiruchirappalli","Madurai"):     {"plazas": 2,  "toll": 460,  "highway": "NH-544"},
    ("Madurai",      "Coimbatore"):    {"plazas": 2,  "toll": 460,  "highway": "NH-544"},
    # NH-30
    ("Chennai",      "Tirupati"):      {"plazas": 2,  "toll": 460,  "highway": "NH-30"},
    ("Tirupati",     "Kadapa"):        {"plazas": 2,  "toll": 460,  "highway": "NH-30"},
    ("Kadapa",       "Kurnool"):       {"plazas": 2,  "toll": 460,  "highway": "NH-30"},
    # NH-340
    ("Belgaum",      "Hubli"):         {"plazas": 1,  "toll": 230,  "highway": "NH-340"},
    ("Hubli",        "Davangere"):     {"plazas": 1,  "toll": 230,  "highway": "NH-340"},
    ("Davangere",    "Mangalore"):     {"plazas": 4,  "toll": 920,  "highway": "NH-340"},
}

# Fuel cost per km for different truck types (₹/km)
FUEL_RATES = {
    "Road":  30,
    "Rail":  18,
}

# Driver cost per hour (₹)
DRIVER_RATE = 380


def get_toll_for_segment(origin, destination):
    key1 = (origin, destination)
    key2 = (destination, origin)
    if key1 in TOLL_PLAZAS:
        return TOLL_PLAZAS[key1]
    if key2 in TOLL_PLAZAS:
        return TOLL_PLAZAS[key2]
    # Estimate if not found: ₹230 per 100km
    return {"plazas": 1, "toll": 230, "highway": "unknown"}


def calculate_trip_cost(path, distance_km, duration_hours,
                         transport_mode, quantity_kg):
    if not path or not distance_km:
        return None

    # Toll cost — sum across all segments
    total_toll = 0
    toll_breakdown = []
    for i in range(len(path) - 1):
        seg = get_toll_for_segment(path[i], path[i+1])
        total_toll += seg["toll"]
        toll_breakdown.append({
            "segment": f"{path[i]} → {path[i+1]}",
            "plazas":  seg["plazas"],
            "toll":    seg["toll"]
        })

    # Fuel/transport cost
    fuel_rate = FUEL_RATES.get(transport_mode, 30)
    fuel_cost = round(distance_km * fuel_rate, 0)

    # Driver cost
    driver_cost = round((duration_hours or 0) * DRIVER_RATE, 0)

    # Loading/unloading
    handling_cost = round(quantity_kg * 0.5, 0)

    # Total
    total_cost = fuel_cost + total_toll + driver_cost + handling_cost

    return {
        "fuel_cost":      int(fuel_cost),
        "toll_cost":      int(total_toll),
        "driver_cost":    int(driver_cost),
        "handling_cost":  int(handling_cost),
        "total_cost":     int(total_cost),
        "toll_breakdown": toll_breakdown,
        "cost_per_km":    round(total_cost / distance_km, 1) if distance_km else 0,
        "transport_mode": transport_mode,
        "distance_km":    distance_km,
        "duration_hours": duration_hours,
    }


if __name__ == "__main__":
    path = ["Hyderabad", "Bangalore", "Mysore", "Coimbatore", "Thrissur", "Kochi"]
    result = calculate_trip_cost(path, 1085.8, 14.3, "Road", 500)
    print("Trip Cost Breakdown:")
    for k, v in result.items():
        if k != "toll_breakdown":
            print(f"  {k:20} : {v}")
    print("\nToll Breakdown:")
    for t in result["toll_breakdown"]:
        print(f"  {t['segment']:35} | {t['plazas']} plazas | ₹{t['toll']}")
    print(f"\n  TOTAL COST: ₹{result['total_cost']:,}")