import os
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import psycopg
from psycopg import errors as pg_errors
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="API Clínica")

DATABASE_URL = os.environ["DATABASE_URL"]


# ------------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------------
def db():
    """Devuelve una conexión con filas en formato dict."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _insert(conn, sql: str, params: tuple):
    """INSERT con manejo amigable de errores de integridad."""
    try:
        return conn.execute(sql, params).fetchone()
    except pg_errors.UniqueViolation as e:
        raise HTTPException(409, f"Conflicto de unicidad: {e.diag.message_detail or e}")
    except pg_errors.ForeignKeyViolation as e:
        raise HTTPException(400, f"Referencia inválida: {e.diag.message_detail or e}")
    except pg_errors.NotNullViolation as e:
        raise HTTPException(400, f"Falta campo requerido: {e.diag.column_name}")


# ------------------------------------------------------------------
# Salud
# ------------------------------------------------------------------
@app.get("/salud")
def salud():
    with db() as conn:
        conn.execute("SELECT 1")
    return {"estado": "ok"}


# ==================================================================
# ESPECIALIDADES
# ==================================================================
class EspecialidadIn(BaseModel):
    nombre_especialidad: str
    descripcion: Optional[str] = None


@app.get("/especialidades")
def listar_especialidades(limite: int = 50):
    with db() as conn:
        return conn.execute(
            "SELECT id_especialidad, nombre_especialidad, descripcion "
            "FROM especialidades ORDER BY id_especialidad LIMIT %s",
            (limite,),
        ).fetchall()


@app.post("/especialidades", status_code=201)
def crear_especialidad(data: EspecialidadIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO especialidades (nombre_especialidad, descripcion) "
            "VALUES (%s, %s) RETURNING id_especialidad, nombre_especialidad, descripcion",
            (data.nombre_especialidad, data.descripcion),
        )


# ==================================================================
# PACIENTES
# ==================================================================
class PacienteIn(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    fecha_nacimiento: date
    genero: str
    telefono: str
    email: Optional[str] = None
    direccion: Optional[str] = None
    contacto_emergencia: Optional[str] = None
    telefono_emergencia: Optional[str] = None


@app.get("/pacientes")
def listar_pacientes(limite: int = 50):
    with db() as conn:
        return conn.execute(
            "SELECT id_paciente, nombre, apellido_paterno, apellido_materno, "
            "fecha_nacimiento, genero, telefono, email, fecha_registro "
            "FROM pacientes ORDER BY id_paciente LIMIT %s",
            (limite,),
        ).fetchall()


@app.get("/pacientes/{id_paciente}")
def obtener_paciente(id_paciente: int):
    with db() as conn:
        fila = conn.execute(
            "SELECT * FROM pacientes WHERE id_paciente = %s", (id_paciente,)
        ).fetchone()
    if not fila:
        raise HTTPException(404, "Paciente no encontrado")
    return fila


@app.post("/pacientes", status_code=201)
def crear_paciente(data: PacienteIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO pacientes (nombre, apellido_paterno, apellido_materno, "
            "fecha_nacimiento, genero, telefono, email, direccion, "
            "contacto_emergencia, telefono_emergencia) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_paciente, nombre, apellido_paterno, fecha_registro",
            (
                data.nombre, data.apellido_paterno, data.apellido_materno,
                data.fecha_nacimiento, data.genero, data.telefono,
                data.email, data.direccion,
                data.contacto_emergencia, data.telefono_emergencia,
            ),
        )


# ==================================================================
# MEDICOS
# ==================================================================
class MedicoIn(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str] = None
    cedula_profesional: str
    email: str
    telefono: str
    estado: str
    id_especialidad: int


@app.get("/medicos")
def listar_medicos(limite: int = 50):
    with db() as conn:
        return conn.execute(
            "SELECT m.*, e.nombre_especialidad "
            "FROM medicos m "
            "JOIN especialidades e ON e.id_especialidad = m.id_especialidad "
            "ORDER BY m.id_medico LIMIT %s",
            (limite,),
        ).fetchall()


@app.post("/medicos", status_code=201)
def crear_medico(data: MedicoIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO medicos (nombre, apellido_paterno, apellido_materno, "
            "cedula_profesional, email, telefono, estado, id_especialidad) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_medico, nombre, apellido_paterno, cedula_profesional",
            (
                data.nombre, data.apellido_paterno, data.apellido_materno,
                data.cedula_profesional, data.email, data.telefono,
                data.estado, data.id_especialidad,
            ),
        )


# ==================================================================
# EXPEDIENTES BASE
# ==================================================================
class ExpedienteIn(BaseModel):
    id_paciente: int
    tipo_sangre: Optional[str] = None
    alergias: Optional[str] = None
    antecedentes_patologicos: Optional[str] = None
    antecedentes_heredofamiliares: Optional[str] = None


@app.get("/expedientes")
def listar_expedientes(limite: int = 50):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM expedientes_base ORDER BY id_expediente LIMIT %s",
            (limite,),
        ).fetchall()


@app.get("/pacientes/{id_paciente}/expediente")
def expediente_de_paciente(id_paciente: int):
    with db() as conn:
        fila = conn.execute(
            "SELECT * FROM expedientes_base WHERE id_paciente = %s",
            (id_paciente,),
        ).fetchone()
    if not fila:
        raise HTTPException(404, "Expediente no encontrado para ese paciente")
    return fila


@app.post("/expedientes", status_code=201)
def crear_expediente(data: ExpedienteIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO expedientes_base (id_paciente, tipo_sangre, alergias, "
            "antecedentes_patologicos, antecedentes_heredofamiliares) "
            "VALUES (%s, %s, %s, %s, %s) "
            "RETURNING id_expediente, id_paciente, fecha_apertura",
            (
                data.id_paciente, data.tipo_sangre, data.alergias,
                data.antecedentes_patologicos, data.antecedentes_heredofamiliares,
            ),
        )


# ==================================================================
# CITAS
# ==================================================================
class CitaIn(BaseModel):
    id_paciente: int
    id_medico: int
    fecha_hora: datetime
    motivo: str
    estado: str
    notas: Optional[str] = None


@app.get("/citas")
def listar_citas(
    limite: int = 50,
    id_paciente: Optional[int] = Query(None),
    id_medico: Optional[int] = Query(None),
):
    sql = "SELECT * FROM citas WHERE 1=1"
    params: list = []
    if id_paciente is not None:
        sql += " AND id_paciente = %s"
        params.append(id_paciente)
    if id_medico is not None:
        sql += " AND id_medico = %s"
        params.append(id_medico)
    sql += " ORDER BY fecha_hora DESC LIMIT %s"
    params.append(limite)

    with db() as conn:
        return conn.execute(sql, tuple(params)).fetchall()


@app.post("/citas", status_code=201)
def crear_cita(data: CitaIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO citas (id_paciente, id_medico, fecha_hora, motivo, estado, notas) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "RETURNING id_cita, id_paciente, id_medico, fecha_hora, estado",
            (data.id_paciente, data.id_medico, data.fecha_hora,
             data.motivo, data.estado, data.notas),
        )


# ==================================================================
# NOTAS DE CONSULTA
# ==================================================================
class NotaIn(BaseModel):
    id_expediente: int
    id_medico: int
    id_cita: Optional[int] = None
    peso: Optional[Decimal] = None
    talla: Optional[Decimal] = None
    presion_arterial: Optional[str] = None
    temperatura: Optional[Decimal] = None
    sintomas: str
    diagnostico: str


@app.get("/notas")
def listar_notas(
    limite: int = 50,
    id_expediente: Optional[int] = Query(None),
):
    sql = "SELECT * FROM notas_consulta WHERE 1=1"
    params: list = []
    if id_expediente is not None:
        sql += " AND id_expediente = %s"
        params.append(id_expediente)
    sql += " ORDER BY fecha_consulta DESC LIMIT %s"
    params.append(limite)

    with db() as conn:
        return conn.execute(sql, tuple(params)).fetchall()


@app.post("/notas", status_code=201)
def crear_nota(data: NotaIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO notas_consulta (id_expediente, id_medico, id_cita, "
            "peso, talla, presion_arterial, temperatura, sintomas, diagnostico) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id_nota, id_expediente, id_medico, fecha_consulta",
            (
                data.id_expediente, data.id_medico, data.id_cita,
                data.peso, data.talla, data.presion_arterial,
                data.temperatura, data.sintomas, data.diagnostico,
            ),
        )


# ==================================================================
# RECETAS
# ==================================================================
class RecetaIn(BaseModel):
    id_nota: int
    vigencia_dias: Optional[int] = 30
    indicaciones_generales: Optional[str] = None


@app.get("/recetas")
def listar_recetas(limite: int = 50, id_nota: Optional[int] = Query(None)):
    if id_nota is not None:
        with db() as conn:
            return conn.execute(
                "SELECT * FROM recetas WHERE id_nota = %s "
                "ORDER BY fecha_emision DESC LIMIT %s",
                (id_nota, limite),
            ).fetchall()
    with db() as conn:
        return conn.execute(
            "SELECT * FROM recetas ORDER BY fecha_emision DESC LIMIT %s",
            (limite,),
        ).fetchall()


@app.get("/recetas/{id_receta}")
def obtener_receta(id_receta: int):
    with db() as conn:
        receta = conn.execute(
            "SELECT * FROM recetas WHERE id_receta = %s", (id_receta,)
        ).fetchone()
        if not receta:
            raise HTTPException(404, "Receta no encontrada")
        detalles = conn.execute(
            "SELECT * FROM detalle_recetas WHERE id_receta = %s ORDER BY num_item",
            (id_receta,),
        ).fetchall()
    return {"receta": receta, "detalles": detalles}


@app.post("/recetas", status_code=201)
def crear_receta(data: RecetaIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO recetas (id_nota, vigencia_dias, indicaciones_generales) "
            "VALUES (%s, COALESCE(%s, 30), %s) "
            "RETURNING id_receta, id_nota, fecha_emision, vigencia_dias",
            (data.id_nota, data.vigencia_dias, data.indicaciones_generales),
        )


# ==================================================================
# ESTUDIOS DE LABORATORIO
# ==================================================================
class EstudioIn(BaseModel):
    id_nota: int
    tipo_estudio: str
    fecha_solicitud: Optional[date] = None
    fecha_resultado: Optional[date] = None
    estado: str
    resultado: Optional[str] = None
    archivo_url: Optional[str] = None


@app.get("/estudios")
def listar_estudios(limite: int = 50, id_nota: Optional[int] = Query(None)):
    if id_nota is not None:
        with db() as conn:
            return conn.execute(
                "SELECT * FROM estudios_laboratorio WHERE id_nota = %s "
                "ORDER BY fecha_solicitud DESC LIMIT %s",
                (id_nota, limite),
            ).fetchall()
    with db() as conn:
        return conn.execute(
            "SELECT * FROM estudios_laboratorio "
            "ORDER BY fecha_solicitud DESC LIMIT %s",
            (limite,),
        ).fetchall()


@app.post("/estudios", status_code=201)
def crear_estudio(data: EstudioIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO estudios_laboratorio (id_nota, tipo_estudio, "
            "fecha_solicitud, fecha_resultado, estado, resultado, archivo_url) "
            "VALUES (%s, %s, COALESCE(%s, CURRENT_DATE), %s, %s, %s, %s) "
            "RETURNING id_estudio, id_nota, tipo_estudio, fecha_solicitud, estado",
            (
                data.id_nota, data.tipo_estudio, data.fecha_solicitud,
                data.fecha_resultado, data.estado, data.resultado,
                data.archivo_url,
            ),
        )


# ==================================================================
# DETALLE DE RECETAS
# ==================================================================
class DetalleRecetaIn(BaseModel):
    id_receta: int
    num_item: int
    medicamento: str
    dosis: str
    frecuencia: str
    duracion: str


@app.get("/recetas/{id_receta}/detalles")
def listar_detalles(id_receta: int):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM detalle_recetas WHERE id_receta = %s ORDER BY num_item",
            (id_receta,),
        ).fetchall()


@app.post("/detalles-receta", status_code=201)
def crear_detalle(data: DetalleRecetaIn):
    with db() as conn:
        return _insert(
            conn,
            "INSERT INTO detalle_recetas (id_receta, num_item, medicamento, "
            "dosis, frecuencia, duracion) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "RETURNING id_detalle, id_receta, num_item",
            (
                data.id_receta, data.num_item, data.medicamento,
                data.dosis, data.frecuencia, data.duracion,
            ),
        )