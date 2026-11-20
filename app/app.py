"""
Sistema de Inventario Tecnológico - Servidores II (UNISON)
Aplicación Flask que registra, consulta, edita y elimina platillos e ingredientes de un restaurante en MySQL.
La configuración de conexión se lee de variables de entorno (archivo .env).
"""
import os
import re
import socket

import pymysql
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "servidores-ii")

CAMPOS = [["titulo", "descripcion", "tipo", "precio", "dispo"], ["nombre", "proporcion", "cantidad"], ["platillo", "ingrediente", "cantidad"]]

def conectar():
    """Abre una conexión con MySQL usando el nombre del servicio (db)."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "app_inventario"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "inventario"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )

def opciones_enum(columna):
    """Lee los valores permitidos de una columna ENUM definida en init.sql.
    Así, los tipos y estados se adaptan editando solo el script SQL."""
    with conectar() as cx, cx.cursor() as cur:
        cur.execute(
            "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'platillos' AND COLUMN_NAME = %s",
            (columna,),
        )
        fila = cur.fetchone()
    definicion = fila["COLUMN_TYPE"] if fila else "enum()"
    return [v.replace("''", "'") for v in re.findall(r"'((?:[^']|'')*)'", definicion)]


@app.context_processor
def datos_servidor():
    """Muestra la organización y qué contenedor atendió la petición."""
    return {"contenedor": socket.gethostname(), "db_host": os.getenv("DB_HOST", "db"),
            "organizacion": os.getenv("ORGANIZACION", "Universidad de Sonora")}


@app.errorhandler(pymysql.err.OperationalError)
def error_bd(error):
    return render_template("error.html", detalle=str(error)), 503

@app.route("/admin")
def inicio():
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("SELECT * FROM platillos ORDER BY id_pla")
        platillos = cur.fetchall()
        cur.execute("SELECT n.platillo AS id_pla, p.titulo AS platillo, n.ingrediente AS id_ing, i.nombre AS ingrediente, CONCAT(i.proporcion, ' x ', n.cantidad) AS cantidad FROM necesita n JOIN ingredientes i ON i.id_ing = n.ingrediente JOIN platillos p ON p.id_pla = n.platillo ORDER BY n.platillo, n.ingrediente")
        necesita = cur.fetchall()
        cur.execute("SELECT * FROM ingredientes ORDER BY id_ing")
        ingredientes = cur.fetchall()
    return render_template("index.html", platillos=platillos, necesita=necesita, ingredientes=ingredientes)

@app.route("/")
def menu():
    categorias = ["Entradas", "Platillos", "Salsas", "Bebidas", "Postres"]
    platillos = []
    with conectar() as cx, cx.cursor() as cur:
        for c in categorias:
            cur.execute("SELECT * FROM platillos WHERE dispo = 1 AND tipo = '" + c + "'")
            if not cur.fetchall():
                categorias.remove(c)
        cur.execute("SELECT * FROM platillos WHERE dispo = 1")
        platillos = cur.fetchall()
    return render_template("menu.html", categorias=categorias, platillos=platillos)

def leer_formulario(campos):
    datos = {campo: request.form.get(campo, "").strip() for campo in campos}
    faltantes = [c for c, v in datos.items() if not v]
    return datos, faltantes

@app.route("/platillo/nuevo", methods=["GET", "POST"])
def platillo_nuevo():
    if request.method == "POST":
        datos, faltantes = leer_formulario(CAMPOS[0])
        if faltantes:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("formulario.html", platillo=datos, tipos=opciones_enum("tipo"), titulo="Registrar platillo")
        try:
            with conectar() as cx, cx.cursor() as cur:
                cur.execute(
                    "INSERT INTO platillos (titulo, descripcion, tipo, precio, dispo)"
                    "VALUES (%(titulo)s, %(descripcion)s, %(tipo)s, %(precio)s, %(dispo)s)",
                    datos,
                )
                cx.commit()
        except pymysql.err.IntegrityError:
            flash("Ya existe un platillo como ese.", "error")
            return render_template("formulario.html", platillo=datos, tipos=opciones_enum("tipo"), titulo="Registrar platillo")
        flash("Platillo registrado correctamente.", "ok")
        return redirect(url_for("inicio"))
    return render_template("formulario.html", platillo={}, tipos=opciones_enum("tipo"), titulo="Registrar platillo")

@app.route("/platillo/editar/<int:id_platillo>", methods=["GET", "POST"])
def platillo_editar(id_platillo):
    if request.method == "POST":
        datos, faltantes = leer_formulario(CAMPOS[0])
        datos["id_pla"] = id_platillo
        if faltantes:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("formulario.html", platillo=datos, tipos=opciones_enum("tipo"), titulo="Editar platillo")
        try:
            with conectar() as cx, cx.cursor() as cur:
                cur.execute(
                    "UPDATE platillos SET titulo=%(titulo)s, descripcion=%(descripcion)s, tipo=%(tipo)s, "
                    "precio=%(precio)s, dispo=%(dispo)s WHERE id=%(id_pla)s",
                    datos,
                )
                cx.commit()
        except pymysql.err.IntegrityError:
            flash("Ya existe un platillo como ese.", "error")
            return render_template("formulario.html", platillo=datos, tipos=opciones_enum("tipo"), titulo="Editar platillo")
        flash("Platillo actualizado.", "ok")
        return redirect(url_for("inicio"))
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("SELECT * FROM platillos WHERE id_pla=%s", (id_platillo,))
        platillo = cur.fetchone()
    if not platillo:
        flash("El platillo no existe.", "error")
        return redirect(url_for("inicio"))
    return render_template("formulario.html", platillo=platillo, tipos=opciones_enum("tipo"), titulo="Editar platillo")

@app.route("/platillo/eliminar/<int:id_platillo>", methods=["POST"])
def platillo_eliminar(id_platillo):
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("DELETE FROM platillos WHERE id_pla=%s", (id_platillo,))
        cx.commit()
    flash("Platillo eliminado.", "ok")
    return redirect(url_for("inicio"))

@app.route("/platillo/cocinar/<int:id_platillo>", methods=["POST"])
def platillo_cocinar(id_platillo):
    try:
        with conectar() as cx, cx.cursor() as cur:
            cur.execute("SELECT * FROM platillos WHERE id_pla=%s", (id_platillo,))
            if cur.fetchone()["dispo"] == 1:
                cur.execute("SELECT * FROM necesita WHERE platillo=%s", (id_platillo,))
                receta = cur.fetchall() 
                if checar_disponibilidad(receta):
                    for i in receta:
                        cur.execute("UPDATE ingredientes SET cantidad = cantidad - %(cantidad)s WHERE id_ing=%(ingrediente)s", i,)
                    cx.commit()
                    flash("Se restaron los ingredientes utilizados.", "ok")
                    checar_dispo_todos()
                    return redirect(url_for("inicio"))
                else:
                    flash("No hay suficientes ingredientes para ese platillo!", "error")
                    cur.execute("UPDATE platillos SET dispo = 0 WHERE id_pla=%s", (id_platillo,))
                    cx.commit()
                    return redirect(url_for("inicio"))
            else:
                flash("No hay suficientes ingredientes para ese platillo!", "error")
                return redirect(url_for("inicio"))
    except pymysql.err.IntegrityError:
        flash("Error de MySQL.", "error")
        return redirect(url_for("inicio"))

def checar_disponibilidad(receta):
    with conectar() as cx, cx.cursor() as cur:
        alldispo = []
        for i in receta:
            cur.execute("SELECT * FROM ingredientes i WHERE i.id_ing = %s", (i["ingrediente"],))
            alldispo.append(float(cur.fetchone()["cantidad"]) >= float(i["cantidad"]))
        return all(alldispo)

def checar_dispo_todos():
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("SELECT * FROM platillos")
        for p in cur.fetchall():
            cur.execute("SELECT * FROM necesita WHERE platillo=%s", (p["id_pla"],))
            if not checar_disponibilidad(cur.fetchall()):
                cur.execute("UPDATE platillos SET dispo = 0 WHERE id_pla=%s", (p["id_pla"],))
                cx.commit()

@app.route("/ingrediente/nuevo", methods=["GET", "POST"])
def ingrediente_nuevo():
    if request.method == "POST":
        datos, faltantes = leer_formulario(CAMPOS[1])
        if faltantes:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("formulario_ingrediente.html", ingrediente=datos, titulo="Registrar ingrediente")
        try:
            with conectar() as cx, cx.cursor() as cur:
                cur.execute(
                    "INSERT INTO ingredientes (nombre, proporcion, cantidad)"
                    "VALUES (%(nombre)s, %(proporcion)s, %(cantidad)s)",
                    datos,
                )
                cx.commit()
        except pymysql.err.IntegrityError:
            flash("Ya existe un ingrediente como ese.", "error")
            return render_template("formulario_ingrediente.html", ingrediente=datos, titulo="Registrar ingrediente")
        flash("Ingrediente registrado correctamente.", "ok")
        return redirect(url_for("inicio"))
    return render_template("formulario_ingrediente.html", ingrediente={}, titulo="Registrar ingrediente")

@app.route("/ingrediente/editar/<int:id_ingrediente>", methods=["GET", "POST"])
def ingrediente_editar(id_ingrediente):
    if request.method == "POST":
        datos, faltantes = leer_formulario(CAMPOS[1])
        datos["id_ing"] = id_ingrediente
        if faltantes:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("formulario_ingrediente.html", ingrediente=datos, titulo="Editar ingrediente")
        try:
            with conectar() as cx, cx.cursor() as cur:
                cur.execute(
                    "UPDATE ingredientes SET nombre=%(nombre)s, cantidad=%(cantidad)s, proporcion=%(proporcion)s WHERE id_ing=%(id_ing)s",
                    datos,
                    )
                cx.commit()
                checar_dispo_todos()
        except pymysql.err.IntegrityError:
            flash("Ya existe un ingrediente como ese.", "error")
            return render_template("formulario_ingrediente.html", ingrediente=datos, titulo="Editar ingrediente")
        flash("Platillo actualizado.", "ok")
        return redirect(url_for("inicio"))
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("SELECT * FROM ingredientes WHERE id_ing=%s", (id_ingrediente,))
        ingrediente = cur.fetchone()
    if not ingrediente:
        flash("El ingrediente no existe.", "error")
        return redirect(url_for("inicio"))
    return render_template("formulario_ingrediente.html", ingrediente=ingrediente, titulo="Editar ingrediente")

@app.route("/ingrediente/eliminar/<int:id_ingrediente>", methods=["POST"])
def ingrediente_eliminar(id_ingrediente):
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("DELETE FROM ingredientes WHERE id_ing=%s", (id_ingrediente,))
        cx.commit()
    flash("Ingrediente eliminado.", "ok")
    return redirect(url_for("inicio"))

@app.route("/ingrediente/cantidad/<int:id_ingrediente>", methods=["GET", "POST"])
def ingrediente_cantidad(id_ingrediente):
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("SELECT * FROM ingredientes WHERE id_ing=%s", (id_ingrediente,))
        ingrediente = cur.fetchone()
    if request.method == "POST":
        datos, faltantes = leer_formulario(["cantidad", "adicion"])
        datos["id_ing"] = id_ingrediente
        if faltantes:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("formulario_ing_cantidad.html", datos=datos, titulo="Gestionar cantidad de ingrediente")
        if float(ingrediente["cantidad"]) + (float(datos["adicion"]) * float(datos["cantidad"])) < 0:
            flash("Se esta quitando mas del ingrediente que existe actualmente.", "error")
            return render_template("formulario_ing_cantidad.html", datos=datos, titulo="Gestionar cantidad de ingrediente")
        try:
            with conectar() as cx, cx.cursor() as cur:
                cantidad = float(ingrediente["cantidad"]) + (float(datos["adicion"]) * float(datos["cantidad"]))
                cur.execute("UPDATE ingredientes SET cantidad=%s WHERE id_ing=%s", (cantidad, id_ingrediente,))
                cx.commit()
                checar_dispo_todos()
        except pymysql.err.IntegrityError:
            flash("Operación imposible.", "error")
            return render_template("formulario_ing_cantidad.html", datos=datos, titulo="Gestionar cantidad de ingrediente")
        flash("Platillo actualizado.", "ok")
        return redirect(url_for("inicio"))
    if not ingrediente:
        flash("El ingrediente no existe.", "error")
        return redirect(url_for("inicio"))
    return render_template("formulario_ing_cantidad.html", datos={}, titulo="Gestionar cantidad de ingrediente")


@app.route("/receta/nuevo", methods=["GET", "POST"])
def receta_nuevo():
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("SELECT * FROM platillos")
        platillos = cur.fetchall()
        cur.execute("SELECT * FROM ingredientes")
        ingredientes = cur.fetchall()
    if request.method == "POST":
        datos, faltantes = leer_formulario(CAMPOS[2])
        if faltantes:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("formulario_recetas.html", receta=datos, platillos=platillos,ingredientes=ingredientes, titulo="Registrar receta")
        try:
            with conectar() as cx, cx.cursor() as cur:
                cur.execute(
                    "INSERT INTO necesita (platillo, ingrediente, cantidad)"
                    "VALUES (%(platillo)s, %(ingrediente)s, %(cantidad)s)",
                    datos,
                )
                cx.commit()
        except pymysql.err.IntegrityError:
            flash("Ya existe una receta como esa.", "error")
            return render_template("formulario_recetas.html", receta=datos, platillos=platillos,ingredientes=ingredientes, titulo="Registrar receta")
        flash("Receta registrado correctamente.", "ok")
        return redirect(url_for("inicio"))
    return render_template("formulario_recetas.html", receta={}, platillos=platillos,ingredientes=ingredientes, titulo="Registrar receta")

@app.route("/receta/editar/<int:platillo>/<int:ingrediente>", methods=["GET", "POST"])
def receta_editar(platillo, ingrediente):
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("SELECT * FROM platillos")
        platillos = cur.fetchall()
        cur.execute("SELECT * FROM ingredientes")
        ingredientes = cur.fetchall()
    if request.method == "POST":
        datos, faltantes = leer_formulario(CAMPOS[2])
        datos["platillo"] = platillo
        datos["ingrediente"] = ingrediente
        if faltantes:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("formulario_recetas.html", receta=datos, platillos=platillos,ingredientes=ingredientes, titulo="Editar receta")
        try:
            with conectar() as cx, cx.cursor() as cur:
                cur.execute(
                    "UPDATE necesita SET platillo=%(platillo)s, ingrediente=%(ingrediente)s, cantidad=%(cantidad)s WHERE platillo=%(platillo)s AND ingrediente=%(ingrediente)s",
                    datos,
                )
                cx.commit()
        except pymysql.err.IntegrityError:
            flash("Ya existe una receta como esa.", "error")
            return render_template("formulario_recetas.html", receta=datos, platillos=platillos,ingredientes=ingredientes, titulo="Editar receta")
        flash("Platillo actualizado.", "ok")
        return redirect(url_for("inicio"))
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("SELECT * FROM necesita WHERE platillo=%s AND ingrediente=%s", (platillo, ingrediente))
        receta = cur.fetchone()
    if not receta:
        flash("La receta no existe.", "error")
        return redirect(url_for("inicio"))
    return render_template("formulario_recetas.html", receta=receta, platillos=platillos,ingredientes=ingredientes, titulo="Editar receta")

@app.route("/receta/eliminar/<int:platillo>/<int:ingrediente>", methods=["POST"])
def receta_eliminar(platillo, ingrediente):
    with conectar() as cx, cx.cursor() as cur:
        cur.execute("DELETE * FROM necesita WHERE platillo=%s AND ingrediente=%s", (platillo, ingrediente))
        cx.commit()
    flash("Receta eliminada.", "ok")
    return redirect(url_for("inicio"))

@app.route("/salud")
def salud():
    """Punto de verificación usado en las prácticas de automatización y respaldo."""
    try:
        with conectar() as cx, cx.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM platillos")
            total = cur.fetchone()["total"]
        return jsonify(estado="ok", base_de_datos="conectada", equipos=total)
    except pymysql.err.MySQLError as e:
        return jsonify(estado="error", base_de_datos="sin conexión", detalle=str(e)), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)