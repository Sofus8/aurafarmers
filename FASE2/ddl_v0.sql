ofamiliares TEXT,
    fecha_apertura TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE citas (
    id_cita SERIAL PRIMARY KEY,
    id_paciente INT NOT NULL REFERENCES pacientes(id_paciente),
    id_medico INT NOT NULL REFERENCES medicos(id_medico),
    fecha_hora TIMESTAMP NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    estado VARCHAR(20) NOT NULL,
    notas TEXT,
    CONSTRAINT unique_medico_horario UNIQUE (id_medico, fecha_hora)
);



CREATE TABLE notas_consulta (
    id_nota SERIAL PRIMARY KEY,
    id_expediente INT NOT NULL REFERENCES expedientes_base(id_expediente),
    id_medico INT NOT NULL REFERENCES medicos(id_medico),
    id_cita INT UNIQUE REFERENCES citas(id_cita),
    fecha_consulta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    peso DECIMAL(5,2),
    talla DECIMAL(4,2),
    presion_arterial VARCHAR(10),
    temperatura DECIMAL(4,1),
    sintomas TEXT NOT NULL,
    diagnostico TEXT NOT NULL
);


CREATE TABLE recetas (
    id_receta SERIAL PRIMARY KEY,
    id_nota INT NOT NULL REFERENCES notas_consulta(id_nota),
    fecha_emision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    vigencia_dias INT NOT NULL DEFAULT 30,
    indicaciones_generales TEXT
);

CREATE TABLE estudios_laboratorio (
    id_estudio SERIAL PRIMARY KEY,
    id_nota INT NOT NULL REFERENCES notas_consulta(id_nota),
    tipo_estudio VARCHAR(100) NOT NULL,
    fecha_solicitud DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_resultado DATE,
    estado VARCHAR(20) NOT NULL,
    resultado TEXT,
    archivo_url VARCHAR(255)
);


CREATE TABLE detalle_recetas (
    id_detalle SERIAL PRIMARY KEY,
    id_receta INT NOT NULL REFERENCES recetas(id_receta),
    num_item INT NOT NULL,
    medicamento VARCHAR(150) NOT NULL,
    dosis VARCHAR(50) NOT NULL,
    frecuencia VARCHAR(50) NOT NULL,
    duracion VARCHAR(50) NOT NULL,
    CONSTRAINT unique_receta_item UNIQUE (id_receta, num_item)
);

--Bryan Hernandez Flores
--Deberiamos regresar a las viejas costumbres de los campos de concentracion Brenda Sofia Cabrera Leon--
-- VIva dios Alessandro PedrozA Martinez--
