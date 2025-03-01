import sqlite3

def init_db():
    conn = sqlite3.connect("farms.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        state TEXT,
        latitude REAL,
        longitude REAL,
        description TEXT
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id INTEGER,
        name TEXT NOT NULL,
        type TEXT,
        working_speed TEXT,
        soil_type TEXT,
        width TEXT,
        operating_cost TEXT,
        details TEXT,
        FOREIGN KEY (farm_id) REFERENCES farms (id)
    );
    """)
    
    # Insert two hard-coded farms
    cursor.execute("""
    INSERT INTO farms (user_id, name, state, latitude, longitude, description)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (1, "Farm 1 - Illinois", "Illinois", 40.865, -88.669, "Illinois Row Crop Farmer"))
    
    cursor.execute("""
    INSERT INTO farms (user_id, name, state, latitude, longitude, description)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (1, "Farm 2 - North Dakota", "North Dakota", 46.872, -97.279, "North Dakota Row Crop Farmer"))
    
    # Insert equipment for Illinois Farm (Farm 1)
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, "No-Till Planting", "16-row No-Till Planter", "5 mph", "Silty Clay Loam", "30 ft", "$55 per acre", "Farmer Owned"))
    
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, "High-Speed Disk", "High-Speed Disk (e.g., Salford Halo)", "8 mph", "Silty Clay Loam", "30 ft", "$50 per acre", "Secondary Tillage/Seedbed Prep, Farmer Owned"))
    
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, "Conventional Disk Harrow", "Large Tandem Disc Harrow", "6 mph", "Silty Clay Loam", "35 ft", "$60 per acre", "Secondary Tillage, Farmer Owned"))
    
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, "Custom Deep Rip with Cover Crop Seeding", "Commercial Deep Rip and Cover Crop Service", "N/A", "N/A", "N/A", "$75 per acre", "Hired Resource – Deep Ripper with Cover Crop Seeder Attachment, Estimated Time: 0.4 hours per acre"))
    
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, "Custom Moldboard Plowing", "Commercial Moldboard Plowing Service", "N/A", "N/A", "N/A", "$90 per acre", "Hired Resource – Large Moldboard Plow, Estimated Time: 0.5 hours per acre"))
    
    # Insert equipment for North Dakota Farm (Farm 2)
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (2, "No-Till Planting", "Air Drill No-Till Planter", "4.5 mph", "Silt Loam", "40 ft", "$47.5", "Farmer Owned"))
    
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (2, "Air Seeder with Disc Coulters", "Air Seeder with Independent Disc Coulters", "5 mph", "Silt Loam", "50 ft", "$39 per acre", "Farmer Owned – for Wheat/Small Grains"))
    
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (2, "Vertical Tillage", "Light Vertical Tillage Tool", "6 mph", "Silt Loam", "35 ft", "$42.5 per acre", "Farmer Owned – Light Residue Management"))
    
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (2, "Custom Strip-Till Application", "Commercial Strip-Till Service", "N/A", "N/A", "N/A", "$55 per acre", "Hired Resource – Strip-Till Implement (8-row or 12-row unit), Estimated Time: 0.2 hours per acre"))
    
    cursor.execute("""
    INSERT INTO equipment (farm_id, name, type, working_speed, soil_type, width, operating_cost, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (2, "Custom Heavy Discing", "Commercial Heavy Discing Service", "N/A", "N/A", "N/A", "$50 per acre", "Hired Resource – Large Offset Disc Harrow, Estimated Time: 0.3 hours per acre"))
    
    conn.commit()
    conn.close()
    print("Database initialized with sample farms and equipment.")

if __name__ == "__main__":
    init_db()
