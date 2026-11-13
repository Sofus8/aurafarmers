El proyecto del consultorio médico cuenta con una base de datos relacional que administra información de pacientes, médicos, especialidades, citas, expedientes clínicos, recetas y estudios de laboratorio.

Para esta fase se propone implementar una simulación de base de datos distribuida mediante fragmentación horizontal y replicación.

La distribución se realizará utilizando esquemas de PostgreSQL que representarán diferentes nodos.

El objetivo es organizar los registros de pacientes, facilitar las consultas especializadas y comprobar los principios de completitud, reconstrucción y disyunción.

La práctica se realizó en PostgreSQL local debido a la finalización del acceso al proyecto de Supabase. Los nodos son simulados y no representan servidores físicos independientes.


# Parte 1. ¿Qué tabla reparto y con qué criterio?

### Tabla que voy a fragmentar

`public.pacientes`

### Tipo de fragmentación

Fragmentación horizontal.

### Columna que determina el reparto

`fecha_nacimiento`

### Justificación

Se seleccionó la tabla `pacientes` porque contiene 10,005 registros, siendo la tabla con mayor cantidad de información de nuestro proyecto.

La fragmentación horizontal permitirá dividir los registros en dos nodos, utilizando la fecha de nacimiento como criterio.

Se propone separar a los pacientes en dos grupos:

- **Nodo de adultos mayores:** pacientes que, al 12 de noviembre de 2026, tienen 60 años o más.
- **Nodo general:** pacientes menores de 60 años en esa misma fecha.

Esta distribución puede facilitar consultas dirigidas a grupos de pacientes que requieren una atención diferenciada.

El criterio utiliza una fecha de corte fija para la simulación académica. En un sistema real, sería necesario actualizar la distribución cuando los pacientes cumplan 60 años.

### Consulta frecuente del negocio que se beneficia

```sql
SELECT
    id_paciente,
    nombre,
    apellido_paterno,
    fecha_nacimiento
FROM nodo_mayores.pacientes
ORDER BY fecha_nacimiento;
```

Esta consulta permite recuperar directamente los pacientes clasificados como adultos mayores sin revisar todos los registros de la tabla original.

### ¿Por qué este criterio y no otro?

Se eligió la fecha de nacimiento porque es una columna existente en la base de datos y permite clasificar los registros mediante condiciones claramente definidas.

Además, el criterio responde a una posible necesidad operativa del consultorio: organizar la atención de pacientes adultos mayores.

---

# Parte 2. Los predicados

Los predicados son las condiciones que determinan a qué fragmento pertenece cada registro.

Se establecieron dos nodos.

| Nodo | Predicado | Filas |
|---|---|---:|
| `nodo_mayores` | `fecha_nacimiento <= DATE '1966-11-12'` | 3074 |
| `nodo_general` | `fecha_nacimiento > DATE '1966-11-12'` | 6931 |
| **Total** | | **10005** |

### Consulta para contar los registros

```sql
SELECT
    COUNT(*) AS total_pacientes,

    COUNT(*) FILTER (
        WHERE fecha_nacimiento <= DATE '1966-11-12'
    ) AS nodo_mayores,

    COUNT(*) FILTER (
        WHERE fecha_nacimiento > DATE '1966-11-12'
    ) AS nodo_general,

    COUNT(*) FILTER (
        WHERE fecha_nacimiento IS NULL
    ) AS pacientes_sin_fecha

FROM public.pacientes;
```

### Resultados obtenidos

- Total de pacientes: 10,005.
- Pacientes del nodo de adultos mayores: 3,074.
- Pacientes del nodo general: 6,931.
- Pacientes sin fecha de nacimiento: 0.

### Comprobación de filas huérfanas

Una fila huérfana es aquella que no cumple ninguno de los predicados establecidos.

Para comprobarlo se utiliza:

```sql
SELECT COUNT(*) AS huerfanas
FROM public.pacientes
WHERE
    COALESCE(
        fecha_nacimiento <= DATE '1966-11-12',
        FALSE
    ) = FALSE

AND

    COALESCE(
        fecha_nacimiento > DATE '1966-11-12',
        FALSE
    ) = FALSE;
```

### Filas huérfanas encontradas

**0 registros.**

### Si hubo, ¿qué decidí hacer con ellas?

No se encontraron filas huérfanas.

Todos los pacientes cuentan con una fecha de nacimiento que permite clasificarlos en alguno de los dos nodos.

Por lo tanto, no fue necesario crear un tercer fragmento ni corregir fechas faltantes.

---

# Parte 3. Crear los nodos en PostgreSQL

Para representar una base de datos distribuida se crearon dos esquemas:

- `nodo_mayores`
- `nodo_general`

Cada esquema contiene una tabla de pacientes que almacena únicamente los registros correspondientes a su predicado.

La tabla original `public.pacientes` se conserva sin modificaciones.

## 3.1. Crear los esquemas

```sql
CREATE SCHEMA nodo_mayores;

CREATE SCHEMA nodo_general;
```

## 3.2. Crear las tablas

Se utiliza `LIKE` para copiar la estructura de la tabla original, incluyendo restricciones y valores predeterminados.

```sql
CREATE TABLE nodo_mayores.pacientes (
    LIKE public.pacientes
    INCLUDING DEFAULTS
    INCLUDING CONSTRAINTS
);

CREATE TABLE nodo_general.pacientes (
    LIKE public.pacientes
    INCLUDING DEFAULTS
    INCLUDING CONSTRAINTS
);
```

## 3.3. Agregar llaves primarias

Cada fragmento debe conservar una llave primaria para identificar sus registros.

```sql
ALTER TABLE nodo_mayores.pacientes
ADD CONSTRAINT pk_pacientes_mayores
PRIMARY KEY (id_paciente);

ALTER TABLE nodo_general.pacientes
ADD CONSTRAINT pk_pacientes_general
PRIMARY KEY (id_paciente);
```

## 3.4. Agregar restricciones CHECK

Estas restricciones evitan que los nodos acepten pacientes que no cumplen su condición de distribución.

```sql
ALTER TABLE nodo_mayores.pacientes
ADD CONSTRAINT chk_mayores
CHECK (
    fecha_nacimiento IS NOT NULL
    AND fecha_nacimiento <= DATE '1966-11-12'
);

ALTER TABLE nodo_general.pacientes
ADD CONSTRAINT chk_general
CHECK (
    fecha_nacimiento IS NOT NULL
    AND fecha_nacimiento > DATE '1966-11-12'
);
```

## 3.5. Distribuir los registros

Se utiliza `INSERT INTO ... SELECT` para copiar los pacientes desde la tabla original.

### Nodo de adultos mayores

```sql
INSERT INTO nodo_mayores.pacientes
SELECT *
FROM public.pacientes
WHERE fecha_nacimiento <= DATE '1966-11-12';
```

**Registros esperados:** 3,074.

### Nodo general

```sql
INSERT INTO nodo_general.pacientes
SELECT *
FROM public.pacientes
WHERE fecha_nacimiento > DATE '1966-11-12';
```

**Registros esperados:** 6,931.

## 3.6. Crear una vista global

Para reconstruir lógicamente la tabla original se utiliza `UNION ALL`.

```sql
CREATE VIEW nodo_mayores.pacientes_global AS

SELECT *
FROM nodo_mayores.pacientes

UNION ALL

SELECT *
FROM nodo_general.pacientes;
```

La vista permite consultar todos los pacientes distribuidos como si pertenecieran a una sola tabla.

---

# Parte 4. Comprobar las reglas de distribución

Para verificar que la fragmentación funciona correctamente, se realizan las siguientes comprobaciones.

## 4.1. Completitud

La completitud significa que ningún registro original se pierde durante la fragmentación.

```sql
SELECT
    (SELECT COUNT(*) FROM public.pacientes)
        AS total_original,

    (SELECT COUNT(*) FROM nodo_mayores.pacientes)
    +
    (SELECT COUNT(*) FROM nodo_general.pacientes)
        AS suma_fragmentos;
```

### Resultado esperado

| Total original | Suma de fragmentos |
|---:|---:|
| 10005 | 10005 |

La suma de los dos fragmentos debe coincidir con la cantidad de registros de la tabla original.

## 4.2. Reconstrucción

La reconstrucción permite recuperar los datos originales a partir de los fragmentos.

```sql
SELECT
    (SELECT COUNT(*) FROM public.pacientes)
        AS total_original,

    (SELECT COUNT(*)
     FROM nodo_mayores.pacientes_global)
        AS total_reconstruido;
```

### Resultado esperado

| Total original | Total reconstruido |
|---:|---:|
| 10005 | 10005 |

También se puede comprobar que los registros sean idénticos mediante:

```sql
SELECT COUNT(*) AS diferencias
FROM (

    (SELECT * FROM public.pacientes
     EXCEPT ALL
     SELECT * FROM nodo_mayores.pacientes_global)

    UNION ALL

    (SELECT * FROM nodo_mayores.pacientes_global
     EXCEPT ALL
     SELECT * FROM public.pacientes)

) AS comparacion;
```

**Resultado esperado: 0 diferencias.**

## 4.3. Disyunción

La disyunción significa que ningún paciente debe aparecer simultáneamente en ambos fragmentos.

```sql
SELECT COUNT(*) AS pacientes_duplicados

FROM nodo_mayores.pacientes m

JOIN nodo_general.pacientes g
ON m.id_paciente = g.id_paciente;
```

**Resultado esperado: 0 registros duplicados.**

## 4.4. Protección mediante CHECK

Se intenta insertar un paciente menor de 60 años en el nodo de adultos mayores.

```sql
BEGIN;

INSERT INTO nodo_mayores.pacientes
SELECT *
FROM public.pacientes
WHERE fecha_nacimiento > DATE '1966-11-12'
ORDER BY id_paciente
LIMIT 1;

ROLLBACK;
```

### Resultado esperado

PostgreSQL debe rechazar la inserción porque el paciente no cumple la condición del nodo.

El error esperado corresponde a la restricción:

`chk_mayores`

Esto demuestra que los fragmentos están protegidos contra registros incorrectamente asignados.

La instrucción `ROLLBACK` permite deshacer la transacción de prueba. Si PostgreSQL deja la transacción en estado fallido después del error, se debe ejecutar `ROLLBACK;` para cerrarla.

### Resumen de las comprobaciones

| Regla | Resultado esperado |
|---|---|
| Completitud | 10005 registros |
| Reconstrucción | 10005 registros |
| Disyunción | 0 duplicados |
| Protección CHECK | Error de restricción |

Estos resultados deben verificarse mediante las consultas ejecutadas y documentarse con capturas de pantalla.

---

# Parte 5. ¿Qué replico y qué no?

La replicación consiste en mantener copias completas de una tabla en varios nodos.

En nuestro proyecto se propone replicar los catálogos pequeños que pueden ser utilizados por ambos grupos de pacientes.

## 5.1. Propuesta de distribución de las demás tablas

| Tabla | Decisión | Justificación |
|---|---|---|
| `pacientes` | Fragmentar | Contiene 10,005 registros y permite dividir pacientes según su edad. |
| `especialidades` | Replicar | Es un catálogo pequeño que puede ser consultado desde ambos nodos. |
| `medicos` | Replicar (propuesta) | Contiene pocos registros de profesionales que pueden atender diferentes pacientes. |
| `citas` | Mantener en `public` | Se conserva el control centralizado de las citas médicas. |
| `expedientes_base` | Mantener en `public` | Contiene información clínica que requiere controles de acceso. |
| `notas_consulta` | Mantener en `public` | Conserva la relación con los registros clínicos. |
| `recetas` | Mantener en `public` | Se mantiene su relación con pacientes y consultas. |
| `detalle_recetas` | Mantener en `public` | Depende de los registros de recetas. |
| `estudios_laboratorio` | Mantener en `public` | Se centralizan los resultados y sus actualizaciones. |

## 5.2. Replicación de especialidades

Se seleccionó la tabla `especialidades` para realizar la demostración de replicación.

La tabla contiene cinco registros.

### Crear las tablas

```sql
CREATE TABLE nodo_mayores.especialidades (
    LIKE public.especialidades
    INCLUDING CONSTRAINTS
    INCLUDING INDEXES
);

CREATE TABLE nodo_general.especialidades (
    LIKE public.especialidades
    INCLUDING CONSTRAINTS
    INCLUDING INDEXES
);
```

### Copiar los registros

```sql
INSERT INTO nodo_mayores.especialidades
SELECT *
FROM public.especialidades;

INSERT INTO nodo_general.especialidades
SELECT *
FROM public.especialidades;
```

### Verificar las copias

```sql
SELECT
    (SELECT COUNT(*)
     FROM public.especialidades)
        AS original,

    (SELECT COUNT(*)
     FROM nodo_mayores.especialidades)
        AS mayores,

    (SELECT COUNT(*)
     FROM nodo_general.especialidades)
        AS general;
```

### Resultado esperado

| Original | Mayores | General |
|---:|---:|---:|
| 5 | 5 | 5 |

## 5.3. Comprobar la consistencia de las réplicas

```sql
SELECT COUNT(*) AS diferencias
FROM (

    (SELECT *
     FROM nodo_mayores.especialidades

     EXCEPT

     SELECT *
     FROM nodo_general.especialidades)

    UNION ALL

    (SELECT *
     FROM nodo_general.especialidades

     EXCEPT

     SELECT *
     FROM nodo_mayores.especialidades)

) AS comparacion;
```

**Resultado esperado: 0 diferencias.**

## 5.4. Si una tabla replicada cambia, ¿cómo mantengo iguales las copias?

Se propone utilizar una tabla principal como fuente de información y establecer un procedimiento de sincronización que propague los cambios a ambos nodos.

Después de cada actualización se debe comprobar que las réplicas contengan los mismos registros.

En esta práctica se realizó una copia inicial de los datos, por lo que las réplicas no se actualizan automáticamente.

## 5.5. ¿Cómo evito que dos nodos generen el mismo ID?

Se pueden utilizar identificadores UUID, rangos de identificadores diferentes para cada nodo o un generador centralizado de identificadores.

Para esta simulación se conservaron los identificadores originales de los pacientes.

Esto permite identificar a cada paciente sin crear nuevos identificadores durante la fragmentación.

## 5.6. Las llaves foráneas de mis fragmentos, ¿a qué tabla apuntan?

En nuestro diseño, las tablas clínicas que permanecen en `public` conservan sus relaciones originales.

Por ejemplo, las citas y expedientes siguen utilizando las referencias establecidas en la base original.

Las tablas fragmentadas de pacientes son copias independientes.

Una llave foránea no puede apuntar directamente a una vista construida mediante `UNION ALL`.

Por ello, si posteriormente se distribuyen también las citas o los expedientes, será necesario rediseñar las referencias para garantizar la integridad de los datos.

---

# Parte 6. Una operación que cruza nodos

## 6.1. Operación propuesta

Se propone realizar una corrección de la fecha de nacimiento de un paciente.

El paciente con identificador `3054` tiene registrada la fecha `1966-11-13`.

Por esta razón pertenece al nodo general.

Supongamos que el consultorio detecta un error administrativo y confirma que su fecha correcta es `1966-11-12`.

La modificación provoca que el paciente deba trasladarse al nodo de adultos mayores.

Para realizar el traslado es necesario modificar dos nodos.

## 6.2. Sentencias SQL que forman la operación

```sql
BEGIN;

-- 1. Insertar al paciente en el nodo de adultos mayores
-- con su fecha de nacimiento corregida.

INSERT INTO nodo_mayores.pacientes (
    id_paciente,
    nombre,
    apellido_paterno,
    apellido_materno,
    fecha_nacimiento,
    genero,
    telefono,
    email,
    direccion,
    contacto_emergencia,
    telefono_emergencia,
    fecha_registro
)

SELECT
    id_paciente,
    nombre,
    apellido_paterno,
    apellido_materno,
    DATE '1966-11-12',
    genero,
    telefono,
    email,
    direccion,
    contacto_emergencia,
    telefono_emergencia,
    fecha_registro

FROM nodo_general.pacientes

WHERE id_paciente = 3054
AND fecha_nacimiento = DATE '1966-11-13';


-- 2. Eliminar el registro del nodo anterior.

DELETE FROM nodo_general.pacientes

WHERE id_paciente = 3054
AND fecha_nacimiento = DATE '1966-11-13';


-- 3. Comprobar en qué nodo se encuentra el paciente.

SELECT
    'Mayores' AS nodo,
    id_paciente,
    nombre,
    fecha_nacimiento

FROM nodo_mayores.pacientes
WHERE id_paciente = 3054

UNION ALL

SELECT
    'General' AS nodo,
    id_paciente,
    nombre,
    fecha_nacimiento

FROM nodo_general.pacientes
WHERE id_paciente = 3054;


-- 4. Deshacer la simulación para conservar
-- los registros originales.

ROLLBACK;
```

Este código representa una operación académica de traslado entre nodos.

En una operación definitiva se utilizaría `COMMIT` después de comprobar que tanto la inserción como la eliminación afectaron exactamente un registro y que los datos son consistentes.

En este ejercicio se utiliza `ROLLBACK` para no modificar permanentemente los datos.

También sería necesario actualizar la fecha de nacimiento en la tabla principal `public.pacientes` si se tratara de una corrección real.

## 6.3. ¿Qué pasa si se ejecuta la primera sentencia y la segunda falla?

Si la inserción en el nodo de adultos mayores funciona, pero la eliminación del nodo general falla y ambos cambios se confirman por separado, el paciente podría quedar registrado en ambos nodos.

Esto provocaría una inconsistencia y violaría el principio de disyunción.

Para evitarlo se utiliza una transacción.

Las instrucciones `BEGIN`, `COMMIT` y `ROLLBACK` permiten controlar que las operaciones se confirmen conjuntamente o se deshagan si ocurre un error.

De esta manera se protege la consistencia de la base de datos.
