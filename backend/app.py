from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import shutil
import os
import time
import json
import numpy as np
from deepface import DeepFace

app = FastAPI()

#enable cors for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#sqlite setup
conn = sqlite3.connect("alerts.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS cameras(
                id  INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                username TEXT,
                password TEXT,
                ip_address TEXT) """)

c.execute("""CREATE TABLE IF NOT EXISTS ppe_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                helmet INTEGER,
                vest INTEGER,
                gloves INTEGER,
                mask INTEGER,
                glasses INTEGER) """)

c.execute("DROP TABLE IF EXISTS employee_embeddings")
c.execute("""CREATE TABLE IF NOT EXISTS employee_embeddings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT,
                embedding BLOB NOT NULL) """)

c.execute("""CREATE TABLE IF NOT EXISTS ppe_alerts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT,
                violation TEXT,
                timestamp TEXT,
                snapshot_path TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS unathorized_alerts( 
                timestamp TEXT,
                snapshot_path TEXT)""")

conn.commit()

#api models

class CameraConfig(BaseModel):
    name: str
    username: str
    password: str
    ip_address: str

class PPEConfig(BaseModel):
    helmet: bool = False
    vest: bool = False
    gloves: bool = False
    mask: bool = False
    glasses: bool = False

#api endpoints

@app.post("/api/camera")
def add_camera(config: CameraConfig):
    c.execute("INSERT INTO cameras (name, username, password, ip_address) VALUES (?,?,?,?)", (config.name, config.username, config.password, config.ip_address))
    conn.commit()
    return {"message":"camera added successfully"}

@app.post("/api/setPPE")
def set_ppe(config: PPEConfig):
    c.execute("DELETE FROM ppe_config")
    c.execute("INSERT INTO ppe_config (helmet, vest, gloves, mask, glasses) VALUES (?, ?, ?, ?, ?)", (int(config.helmet), int(config.vest), int(config.gloves),
         int(config.mask), int(config.glasses)))
    conn.commit()
    return{"message":"ppe configuration updated"}

@app.post("/api/employees")
def upload_employee(employee_id: str = Form(...), file: UploadFile = File(...)):
    os.makedirs("tmp_employee_images", exist_ok=True)
    tmp_path = f"tmp_employee_images/{employee_id}_{file.filename}"

    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:

        embedding_obj= DeepFace.represent(img_path= tmp_path, model_name="Facenet")[0]["embedding"]
        embedding_json = json.dumps(embedding_obj)

        c.execute("INSERT OR REPLACE INTO employee_embeddings (employee_id, embedding) VALUES (?,?)",
                  (employee_id, embedding_json))
        conn.commit()

    finally:
        os.remove(tmp_path)

    return {"message":"Embedding for {employee_id} stored successfully"}

@app.get("/api/ppe_alerts")
def get_ppe_alerts():
    c.execute("SELECT employee_id, violation, timestamp, snapshot_path FROM ppe_alerts ORDER BY timestamp DESC ")
    rows = c.fetchall()
    return {"ppe alerts": [{"employee_id":r[0], "violation":r[1], "timestamp":r[2], 
                            "snapshot_path":r[3]} for r in rows]}

@app.get("/api/unauthorized_alerts")
def get_unauthorized_alerts():
    c.execute("SELECT timestamp, snapshot_path FROM unauthorized_alerts ORDER BY timestamp DESC ")
    rows = c.fetchall()
    return {"unauthorized access alerts": [{"timestamp":r[0], "snapshot_path":r[1]} for r in rows]}