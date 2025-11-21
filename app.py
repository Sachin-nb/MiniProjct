from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3, os

app = Flask(__name__)
app.secret_key = "super-secret-key"

DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "university_rankings.db")


# ----------------------------------------------------
#  DB CONNECTION
# ----------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------------------------------
#  CREATE TABLE IF NOT EXISTS
# ----------------------------------------------------
def create_table():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            Rank INTEGER,
            institution TEXT,
            location TEXT,
            "location code" TEXT,
            "score scaled" REAL,
            "ar score" REAL,
            "er score" REAL,
            "fsr score" REAL,
            "cpf score" REAL,
            "ifr score" REAL,
            "isr score" REAL
        )
    """)
    conn.commit()
    conn.close()

create_table()


# ----------------------------------------------------
#  REORDER RANKS BASED ON SCORE DESC
# ----------------------------------------------------
def reorder_ranks():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT institution, location, "location code",
               "score scaled", "ar score", "er score",
               "fsr score", "cpf score", "ifr score", "isr score"
        FROM rankings
        ORDER BY "score scaled" DESC
    """)
    rows = c.fetchall()

    c.execute("DELETE FROM rankings")

    rank = 1
    for r in rows:
        c.execute("""
            INSERT INTO rankings
            (Rank, institution, location, "location code", "score scaled",
             "ar score", "er score", "fsr score", "cpf score", "ifr score", "isr score")
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rank, r["institution"], r["location"], r["location code"],
            r["score scaled"], r["ar score"], r["er score"], r["fsr score"],
            r["cpf score"], r["ifr score"], r["isr score"]
        ))
        rank += 1

    conn.commit()
    conn.close()


# ----------------------------------------------------
#  HOME PAGE
# ----------------------------------------------------
@app.route("/")
def index():
    conn = get_db()
    rows = conn.execute("SELECT * FROM rankings ORDER BY Rank ASC LIMIT 50").fetchall()
    conn.close()
    return render_template("index.html", universities=rows)


# ----------------------------------------------------
#  UNIVERSITY DETAIL
# ----------------------------------------------------
@app.route("/university/<int:rank>")
def university_detail(rank):
    conn = get_db()
    row = conn.execute("SELECT * FROM rankings WHERE Rank=?", (rank,)).fetchone()
    conn.close()

    if not row:
        flash("University not found!", "error")
        return redirect(url_for("index"))

    return render_template("university_detail.html", university=row)

@app.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()
    country = request.args.get("country", "").strip().lower()

    conn = get_db()
    c = conn.cursor()

    # Case 1: No search query -> show only 10 universities
    if q == "" and country == "":
        rows = c.execute("""
            SELECT * FROM rankings
            ORDER BY Rank ASC
            LIMIT 10
        """).fetchall()

    # Case 2: Search by name only
    elif q != "" and country == "":
        rows = c.execute("""
            SELECT * FROM rankings
            WHERE LOWER(institution) LIKE ?
            ORDER BY Rank ASC
        """, (f"%{q}%",)).fetchall()

    # Case 3: Search by country only
    elif q == "" and country != "":
        rows = c.execute("""
            SELECT * FROM rankings
            WHERE LOWER(location) LIKE ?
            ORDER BY Rank ASC
        """, (f"%{country}%",)).fetchall()

    # Case 4: Search both name + country
    else:
        rows = c.execute("""
            SELECT * FROM rankings
            WHERE LOWER(institution) LIKE ?
              AND LOWER(location) LIKE ?
            ORDER BY Rank ASC
        """, (f"%{q}%", f"%{country}%")).fetchall()

    conn.close()
    return render_template("search.html",
                           universities=rows,
                           query=q,
                           country=country)


# ----------------------------------------------------
#  STATISTICS PAGE
# ----------------------------------------------------
@app.route("/statistics")
def statistics():
    conn = get_db()
    c = conn.cursor()

    total = c.execute("SELECT COUNT(*) FROM rankings").fetchone()[0]
    countries = c.execute("SELECT COUNT(DISTINCT location) FROM rankings").fetchone()[0]
    top_country = c.execute("""
        SELECT location, COUNT(*) as cnt
        FROM rankings GROUP BY location
        ORDER BY cnt DESC LIMIT 1
    """).fetchone()

    conn.close()

    return render_template("statistics.html", stats={
        "total_universities": total,
        "total_countries": countries,
        "top_country": top_country["location"] if top_country else "",
        "top_country_count": top_country["cnt"] if top_country else 0
    })


# ----------------------------------------------------
#  ABOUT PAGE
# ----------------------------------------------------
@app.route("/about")
def about():
    return render_template("about.html")


# ----------------------------------------------------
#  ADD UNIVERSITY
# ----------------------------------------------------
@app.route("/add", methods=["GET", "POST"])
def add_university():

    if request.method == "POST":
        try:
            data = request.form

            inst = data["institution"].strip()
            loc = data["location"].strip()

            # CHECK DUPLICATE
            conn = get_db()
            c = conn.cursor()

            c.execute("""
                SELECT 1 FROM rankings
                WHERE LOWER(institution)=LOWER(?)
                AND LOWER(location)=LOWER(?)
            """, (inst, loc))

            if c.fetchone():
                conn.close()
                return jsonify({
                    "success": False,
                    "message": "This university already exists!"
                })

            # safe float
            def f(v):
                try: return float(v)
                except: return None

            # Insert TEMP row
            c.execute("""
                INSERT INTO rankings
                (Rank, institution, location, "location code",
                 "score scaled", "ar score", "er score", "fsr score",
                 "cpf score", "ifr score", "isr score")
                VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inst, loc, data["location_code"], f(data["overall_score"]),
                f(data["ar_score"]), f(data["er_score"]), f(data["fsr_score"]),
                f(data["cpf_score"]), f(data["ifr_score"]), f(data["isr_score"])
            ))

            conn.commit()
            conn.close()

            reorder_ranks()

            return jsonify({
                "success": True,
                "message": "University added based on overall score!"
            })

        except Exception as e:
            print("ADD ERROR:", e)
            return jsonify({"success": False, "message": "Failed to add university!"})

    return render_template("add_university.html")


# ----------------------------------------------------
#  EDIT UNIVERSITY
# ----------------------------------------------------
@app.route("/edit/<int:rank>", methods=["GET", "POST"])
def edit_university(rank):
    conn = get_db()
    c = conn.cursor()

    row = c.execute("SELECT * FROM rankings WHERE Rank=?", (rank,)).fetchone()
    if not row:
        conn.close()
        flash("University not found!", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            data = request.form

            def f(v):
                try: return float(v)
                except: return None

            c.execute("""
                UPDATE rankings SET
                    institution=?, location=?, "location code"=?,
                    "score scaled"=?, "ar score"=?, "er score"=?,
                    "fsr score"=?, "cpf score"=?, "ifr score"=?, "isr score"=?
                WHERE Rank=?
            """, (
                data["institution"], data["location"], data["location_code"],
                f(data["overall_score"]), f(data["ar_score"]),
                f(data["er_score"]), f(data["fsr_score"]), f(data["cpf_score"]),
                f(data["ifr_score"]), f(data["isr_score"]), rank
            ))

            conn.commit()
            conn.close()

            reorder_ranks()

            flash("University updated!", "success")
            return redirect(url_for("university_detail", rank=rank))

        except Exception as e:
            print("EDIT ERROR:", e)
            flash("Error updating university!", "error")

    conn.close()
    return render_template("edit_university.html", university=row)


# ----------------------------------------------------
#  DELETE UNIVERSITY
# ----------------------------------------------------
@app.route("/delete/<int:rank>", methods=["POST"])
def delete_university(rank):
    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM rankings WHERE Rank=?", (rank,))
    conn.commit()
    conn.close()

    reorder_ranks()

    flash("University deleted successfully!", "success")
    return redirect(url_for("index"))


# ----------------------------------------------------
#  RUN SERVER
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
