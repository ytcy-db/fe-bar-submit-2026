"""One-time Lakebase setup run by the project owner: let the app service principal
create/own its operational schema (crm_ops) and read the published `serving` schema.

usage: python lakebase/grant_app_role.py --profile Azure-ytcy-east2 --sp <app_sp_client_id>
"""
import argparse, json, subprocess
import psycopg2

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True)
ap.add_argument("--sp", required=True)
ap.add_argument("--endpoint", default="projects/officepulse-crm/branches/production/endpoints/primary")
args = ap.parse_args()
cli = "/opt/homebrew/bin/databricks"


def run(*a):
    return json.loads(subprocess.run([cli, *a, "--profile", args.profile, "-o", "json"], capture_output=True, text=True, check=True).stdout)


host = run("postgres", "get-endpoint", args.endpoint)["status"]["hosts"]["host"]
token = run("postgres", "generate-database-credential", args.endpoint)["token"]
user = run("current-user", "me")["userName"]
conn = psycopg2.connect(host=host, dbname="databricks_postgres", user=user, password=token, sslmode="require")
conn.autocommit = True
cur = conn.cursor()
for sql in [
    f'GRANT CONNECT, CREATE ON DATABASE databricks_postgres TO "{args.sp}"',
    "CREATE SCHEMA IF NOT EXISTS serving",
    f'GRANT USAGE ON SCHEMA serving TO "{args.sp}"',
    f'GRANT SELECT ON ALL TABLES IN SCHEMA serving TO "{args.sp}"',
    f'ALTER DEFAULT PRIVILEGES IN SCHEMA serving GRANT SELECT ON TABLES TO "{args.sp}"',
]:
    cur.execute(sql)
    print("ok:", sql)
cur.execute("SELECT rolname FROM pg_roles WHERE rolname = %s", (args.sp,))
print("role present:", cur.fetchone())
