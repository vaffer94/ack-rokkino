"""Test manuale Fase 1: inserisce record finti e li rilegge."""
import db

db.init_db()

db.insert_sensor_reading(temperature=22.5, humidity=45.0, gas=120, lux=300.0, alarm_state=0)
db.insert_sensor_reading(temperature=23.1, humidity=44.2, gas=135, lux=280.5, alarm_state=0)
db.insert_sensor_reading(temperature=28.9, humidity=40.0, gas=560, lux=150.0, alarm_state=1)

db.insert_weather_reading(temperature=21.0, humidity=55.0, description="cielo sereno")
db.insert_weather_reading(temperature=20.4, humidity=60.0, description="poco nuvoloso")

print("=== sensor_readings (today) ===")
for row in db.get_readings("sensor_readings", "today"):
    print(row)

print("\n=== weather_readings (today) ===")
for row in db.get_readings("weather_readings", "today"):
    print(row)

print("\n=== sensor_readings (week) ===")
print(f"{len(db.get_readings('sensor_readings', 'week'))} record")

print("\n=== window_events ===")
print("prima di inserire:", db.get_last_window_event())
db.insert_window_event("opened")
print("dopo 'opened':", db.get_last_window_event())
db.insert_window_event("closed_notified")
print("dopo 'closed_notified':", db.get_last_window_event())
