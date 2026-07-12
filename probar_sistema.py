import os
import json
import pandas as pd

def probar_sistema():
    json_path = 'data_moodle.json'
    excel_path = 'prueba_palpable.xlsx'

    print("====================================================================")
    print("SISTEMA DE ANALÍTICA ACADÉMICA UTTEC - SCRIPT DE EVALUACIÓN LOCAL")
    print("====================================================================")

    # 1. Verificar existencia del archivo local
    if not os.path.exists(json_path):
        print(f"Error: No se encontró el archivo de datos local '{json_path}'.")
        print("Por favor, asegúrate de que el dashboard haya sincronizado previamente los datos.")
        return

    # 2. Leer archivo JSON
    print(f"Leyendo registros desde '{json_path}'...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = data.get('records', [])
    if not records:
        print("Error: El archivo de datos no contiene ningún registro.")
        return

    # 3. Cargar en Pandas DataFrame
    df = pd.DataFrame(records)
    print(f"Total de registros cargados en memoria: {len(df)}")

    # 4. Seleccionar un grupo específico con suficientes estudiantes (ej. DSM 2024-3-1 o el primero que tenga)
    grupos_disponibles = df['grupo'].unique()
    grupo_objetivo = None
    for g in ['DSM 2024-3-1', 'IRD 2025-3-1', 'DSM 2024-3-2', 'IRD 2025-3-2']:
        if g in grupos_disponibles:
            grupo_objetivo = g
            break
    
    if not grupo_objetivo:
        grupo_objetivo = grupos_disponibles[0] if len(grupos_disponibles) > 0 else None

    if not grupo_objetivo:
        print("Error: No se detectaron grupos válidos en la base de datos.")
        return

    print(f"\nGrupo seleccionado para la muestra de prueba: '{grupo_objetivo}'")

    # 5. Filtrar por el grupo seleccionado
    df_grupo = df[df['grupo'] == grupo_objetivo]
    print(f"Total de estudiantes en este grupo: {len(df_grupo)}")

    # 6. Tomar una muestra pequeña de 5 alumnos
    df_muestra = df_grupo.head(5).copy()

    # 7. Calcular Estatus Académico según escala UTTEC (aprobatorio >= 6.0)
    df_muestra['Estatus'] = df_muestra['calificacion_final'].apply(
        lambda x: 'Aprobado (>= 6.0)' if x >= 6.0 else 'En Riesgo (< 6.0)'
    )

    # Reordenar y renombrar columnas para mejor presentación
    df_muestra_tabla = df_muestra[[
        'carrera', 'curso', 'grupo', 'nombre_alumno', 'calificacion_final', 'Estatus'
    ]].rename(columns={
        'carrera': 'Carrera / División',
        'curso': 'Curso Moodle',
        'grupo': 'Grupo Académico',
        'nombre_alumno': 'Nombre Estudiante',
        'calificacion_final': 'Calificación Final'
    })

    # 8. Mostrar la tabla comparativa en la consola
    print("\n--------------------------------------------------------------------")
    print("MUESTRA EVALUADA DE ESTUDIANTES (IMPRESIÓN LOCAL INSTANTÁNEA)")
    print("--------------------------------------------------------------------")
    # Imprimir usando tabulado nativo de Pandas
    print(df_muestra_tabla.to_string(index=False))
    print("--------------------------------------------------------------------")

    # 9. Exportar la muestra a Excel
    print(f"\nExportando esta muestra palpable a '{excel_path}'...")
    try:
        df_muestra_tabla.to_excel(excel_path, index=False, sheet_name='Prueba UTTEC')
        print(f"¡Éxito! Archivo de prueba física generado correctamente en: {os.path.abspath(excel_path)}")
        print("El archivo está listo para ser presentado al asesor académico como evidencia palpable.")
    except Exception as e:
        print(f"Error al generar el archivo Excel: {e}")

    print("====================================================================")

if __name__ == '__main__':
    probar_sistema()
