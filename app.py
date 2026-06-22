from flask import Flask, jsonify
import pandas as pd
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Servidor uttec activado"

@app.route('/analisis')
def analizar_datos():
    ruta_archivo = 'datos.ods'
    
    if not os.path.exists(ruta_archivo):
        return jsonify({"error": "No se encontró el archivo datos.ods en el servidor"}), 404
    
    df = pd.read_excel(ruta_archivo, engine='odf')
    
    df = df.dropna(subset=[df.columns[0]]) 
    
    resultados = []
    
   
    for index, fila in df.iterrows():
      
        alumno_nombre = str(fila.get(df.columns[0], f"Alumno_{index}"))
        
       
        nota_final = fila.get('Total del curso', 0)
        try:
            nota_final = float(nota_final)
        except:
            nota_final = 0.0
            
       
        puntos_riesgo = 0
        alertas = []
        
       
        if nota_final < 60.0: 
            puntos_riesgo += 4
            alertas.append("Calificación actual reprobatoria")
            
      
        tareas_no_entregadas = 0
        for col in df.columns:
            if 'Tarea' in col or 'Cuestionario' in col:
                if pd.isna(fila[col]) or fila[col] == '-' or fila[col] == 0:
                    tareas_no_entregadas += 1
                    
        if tareas_no_entregadas > 2:
            puntos_riesgo += 3
            alertas.append(f"Tiene {tareas_no_entregadas} tareas sin realizar")
            
       
        if puntos_riesgo >= 7:
            estatus = "Riesgo Alto"
        elif puntos_riesgo >= 4:
            estatus = "Riesgo Medio"
        else:
            estatus = "Regular / Sin Riesgo"
            
        resultados.append({
            "alumno": alumno_nombre,
            "nota_final_estimada": nota_final,
            "tareas_faltantes": tareas_no_entregadas,
            "nivel_de_riesgo": estatus,
            "alertas": alertas
        })
        
    return jsonify({
        "curso": "Propedéutico DTIC",
        "total_alumnos_analizados": len(resultados),
        "alumnos": resultados
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
