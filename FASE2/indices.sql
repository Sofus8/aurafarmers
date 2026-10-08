--sofus 8 Indice 3
ANALYZE pacientes;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id_paciente, nombre, apellido_paterno, telefono
FROM pacientes
WHERE email IS NULL;

--Sofus8 Indice 4 
CREATE INDEX pacientes_genero_fecha_idx 
ON pacientes (lower(genero), fecha_registro DESC);
ANALYZE pacientes;
--explain
EXPLAIN (ANALYZE, BUFFERS)
SELECT id_paciente, nombre, apellido_paterno, fecha_registro
FROM pacientes
WHERE lower(genero) = 'femenino'
ORDER BY fecha_registro DESC
LIMIT 10;