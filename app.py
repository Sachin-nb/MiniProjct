# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import sqlite3
import os
import csv

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flash messages

# Paths
DATA_DIR = 'data'
CSV_FILENAME = '2023 QS World University Rankings.csv'
CSV_PATH = os.path.join(DATA_DIR, CSV_FILENAME)
DB_FILENAME = 'university_rankings.db'
DB_PATH = os.path.join(DATA_DIR, DB_FILENAME)

# If DB file is not in data/ but exists at project root, fall back to that
if not os.path.exists(DB_PATH) and os.path.exists(DB_FILENAME):
    DB_PATH = DB_FILENAME

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        pass  # ignore if can't create; we'll assume files are placed correctly

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_table_if_not_exists():
    """Create rankings table if missing. Columns chosen to match your CSV and templates."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            Rank INTEGER PRIMARY KEY,
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
            -- add additional columns here if your CSV contains them
        )
    """)
    conn.commit()
    conn.close()

def import_csv_to_db_if_needed():
    """If DB table is empty and CSV exists, import CSV into DB once.
       This is a one-time helper so your DB gets populated if you only uploaded the CSV."""
    create_table_if_not_exists()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rankings")
    count = cur.fetchone()[0]
    if count == 0 and os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = []
                for r in reader:
                    # Try to coerce scores to float if present
                    def _flt(val):
                        try:
                            return float(val)
                        except Exception:
                            return None
                    rank_val = r.get('Rank') or r.get('rank') or None
                    if rank_val is None or rank_val == '':
                        continue
                    try:
                        rank_int = int(float(rank_val))
                    except Exception:
                        # if rank is like '201-250' or similar, skip numeric conversion; set NULL (or handle differently)
                        try:
                            rank_int = int(rank_val.split('-')[0])
                        except Exception:
                            continue

                    rows.append((
                        rank_int,
                        r.get('institution', ''),
                        r.get('location', ''),
                        r.get('location code', '') or r.get('location_code', '') or '',
                        _flt(r.get('score scaled') or r.get('score_scaled') or r.get('score') or None),
                        _flt(r.get('ar score') or r.get('ar_score')),
                        _flt(r.get('er score') or r.get('er_score')),
                        _flt(r.get('fsr score') or r.get('fsr_score')),
                        _flt(r.get('cpf score') or r.get('cpf_score')),
                        _flt(r.get('ifr score') or r.get('ifr_score')),
                        _flt(r.get('isr score') or r.get('isr_score'))
                    ))
            # Insert rows
            cur.executemany("""
                INSERT OR REPLACE INTO rankings
                (Rank, institution, location, "location code", "score scaled", "ar score", "er score",
                 "fsr score", "cpf score", "ifr score", "isr score")
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
        except Exception as e:
            print("CSV -> DB import error:", e)
    conn.close()

# Ensure table exists and import CSV if DB empty
create_table_if_not_exists()
import_csv_to_db_if_needed()


# ---------- Helper functions ----------
def row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}

def fetch_top_n(n=100):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rankings WHERE Rank IS NOT NULL ORDER BY Rank ASC LIMIT ?", (n,))
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def fetch_by_rank(rank):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rankings WHERE Rank = ?", (rank,))
    row = cur.fetchone()
    conn.close()
    return row_to_dict(row)

def search_universities(query='', country=''):
    conn = get_db_connection()
    cur = conn.cursor()
    q_parts = []
    params = []
    base_sql = "SELECT * FROM rankings WHERE 1=1"
    if query:
        base_sql += " AND LOWER(institution) LIKE ?"
        params.append(f"%{query.lower()}%")
    if country:
        base_sql += " AND LOWER(location) LIKE ?"
        params.append(f"%{country.lower()}%")
    base_sql += " ORDER BY Rank ASC"
    cur.execute(base_sql, params)
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]

def get_next_rank():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(Rank) FROM rankings")
    mx = cur.fetchone()[0]
    conn.close()
    return (int(mx) + 1) if mx is not None else 1


# ---------- Routes ----------
@app.route('/')
def index():
    """Home page with top 100 universities (from DB)"""
    universities = fetch_top_n(100)
    return render_template('index.html', universities=universities)


@app.route('/university/<int:rank>')
def university_detail(rank):
    """Detail page for a specific university"""
    uni = fetch_by_rank(rank)
    if not uni:
        flash('University not found', 'error')
        return redirect(url_for('index'))
    return render_template('university_detail.html', university=uni)


@app.route('/search')
def search():
    """Search universities by name or location.
       Important: If no q and no country provided, return TOP 10 (Rank 1..10)."""
    query = request.args.get('q', '').strip()
    country = request.args.get('country', '').strip()

    if not query and not country:
        # Return top 10 by Rank
        results = fetch_top_n(10)
    else:
        results = search_universities(query=query, country=country)
        # If you want to always limit search results to 10, uncomment:
        # results = results[:10]

    return render_template('search.html', universities=results, query=query, country=country)


@app.route('/api/countries')
def get_countries():
    """API endpoint to get list of countries"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT location FROM rankings WHERE location IS NOT NULL ORDER BY location")
    rows = cur.fetchall()
    conn.close()
    countries = [r['location'] for r in rows]
    return jsonify(countries)


@app.route('/api/universities')
def get_universities_api():
    """API endpoint for university data with pagination"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    start = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rankings")
    total = cur.fetchone()[0]

    cur.execute("SELECT * FROM rankings ORDER BY Rank ASC LIMIT ? OFFSET ?", (per_page, start))
    rows = cur.fetchall()
    conn.close()
    universities = [row_to_dict(r) for r in rows]

    return jsonify({
        'universities': universities,
        'total': total,
        'page': page,
        'per_page': per_page
    })


@app.route('/statistics')
def statistics():
    """Statistics page (computed from DB)"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM rankings")
    total_universities = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT location) FROM rankings")
    total_countries = cur.fetchone()[0]

    cur.execute("SELECT location, COUNT(*) as cnt FROM rankings GROUP BY location ORDER BY cnt DESC LIMIT 1")
    top_country_row = cur.fetchone()
    if top_country_row:
        top_country = top_country_row['location']
        top_country_count = top_country_row['cnt']
    else:
        top_country = ''
        top_country_count = 0

    conn.close()

    stats = {
        'total_universities': total_universities,
        'total_countries': total_countries,
        'top_country': top_country,
        'top_country_count': top_country_count
    }

    return render_template('statistics.html', stats=stats)


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/add', methods=['GET', 'POST'])
def add_university():
    """Add a new university - save to DB (not CSV)"""
    if request.method == 'POST':
        data = {
            'institution': request.form.get('institution', '').strip(),
            'location': request.form.get('location', '').strip(),
            'location_code': request.form.get('location_code', '').strip(),
            'ar_score': request.form.get('ar_score') or None,
            'er_score': request.form.get('er_score') or None,
            'fsr_score': request.form.get('fsr_score') or None,
            'cpf_score': request.form.get('cpf_score') or None,
            'ifr_score': request.form.get('ifr_score') or None,
            'isr_score': request.form.get('isr_score') or None,
            'overall_score': request.form.get('overall_score') or None
        }

        # determine next available unique Rank
        try:
            next_rank = get_next_rank()
        except Exception:
            next_rank = None

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO rankings
                (Rank, institution, location, "location code", "score scaled", "ar score", "er score",
                 "fsr score", "cpf score", "ifr score", "isr score")
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                next_rank,
                data['institution'],
                data['location'],
                data['location_code'],
                float(data['overall_score']) if data['overall_score'] not in (None, '') else None,
                float(data['ar_score']) if data['ar_score'] not in (None, '') else None,
                float(data['er_score']) if data['er_score'] not in (None, '') else None,
                float(data['fsr_score']) if data['fsr_score'] not in (None, '') else None,
                float(data['cpf_score']) if data['cpf_score'] not in (None, '') else None,
                float(data['ifr_score']) if data['ifr_score'] not in (None, '') else None,
                float(data['isr_score']) if data['isr_score'] not in (None, '') else None
            ))
            conn.commit()
            flash('University added to database', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Rank conflict or invalid data — university not added', 'error')
            return redirect(url_for('add_university'))
        except Exception as e:
            print("Add error:", e)
            flash('An error occurred while adding the university', 'error')
            return redirect(url_for('add_university'))
        finally:
            conn.close()
    else:
        return render_template('add_university.html')


@app.route('/edit/<int:rank>', methods=['GET', 'POST'])
def edit_university(rank):
    """Edit an existing university — update DB"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rankings WHERE Rank = ?", (rank,))
    row = cur.fetchone()
    if not row:
        conn.close()
        flash('University not found', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            cur.execute("""
                UPDATE rankings SET
                institution = ?,
                location = ?,
                "location code" = ?,
                "score scaled" = ?,
                "ar score" = ?,
                "er score" = ?,
                "fsr score" = ?,
                "cpf score" = ?,
                "ifr score" = ?,
                "isr score" = ?
                WHERE Rank = ?
            """, (
                request.form.get('institution', '').strip(),
                request.form.get('location', '').strip(),
                request.form.get('location_code', '').strip(),
                float(request.form.get('overall_score')) if request.form.get('overall_score') not in (None, '') else None,
                float(request.form.get('ar_score')) if request.form.get('ar_score') not in (None, '') else None,
                float(request.form.get('er_score')) if request.form.get('er_score') not in (None, '') else None,
                float(request.form.get('fsr_score')) if request.form.get('fsr_score') not in (None, '') else None,
                float(request.form.get('cpf_score')) if request.form.get('cpf_score') not in (None, '') else None,
                float(request.form.get('ifr_score')) if request.form.get('ifr_score') not in (None, '') else None,
                float(request.form.get('isr_score')) if request.form.get('isr_score') not in (None, '') else None,
                rank
            ))
            conn.commit()
            flash('University updated', 'success')
            return redirect(url_for('university_detail', rank=rank))
        except Exception as e:
            print("Edit error:", e)
            flash('An error occurred while updating', 'error')
            return redirect(url_for('edit_university', rank=rank))
        finally:
            conn.close()
    else:
        uni = row_to_dict(row)
        conn.close()
        return render_template('edit_university.html', university=uni)


@app.route('/delete/<int:rank>', methods=['POST'])
def delete_university(rank):
    """Delete a university from DB"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rankings WHERE Rank = ?", (rank,))
    if cur.fetchone() is None:
        conn.close()
        flash('University not found', 'error')
        return redirect(url_for('index'))

    try:
        cur.execute("DELETE FROM rankings WHERE Rank = ?", (rank,))
        conn.commit()
        flash('University deleted', 'success')
    except Exception as e:
        print("Delete error:", e)
        flash('Error deleting university', 'error')
    finally:
        conn.close()

    return redirect(url_for('index'))


if __name__ == '__main__':
    # Start server
    app.run(debug=True, host='0.0.0.0', port=5000)
