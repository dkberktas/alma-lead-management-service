#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
API="$BASE_URL/api"
PASS=0
FAIL=0

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }

assert_status() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    green "  PASS: $label (HTTP $actual)"
    PASS=$((PASS + 1))
  else
    red "  FAIL: $label — expected $expected, got $actual"
    FAIL=$((FAIL + 1))
  fi
}

assert_field() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    green "  PASS: $label = $actual"
    PASS=$((PASS + 1))
  else
    red "  FAIL: $label — expected '$expected', got '$actual'"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "================================================"
echo "  Alma Lead Management — Smoke Test"
echo "  Target: $BASE_URL"
echo "================================================"

# ----------------------------------------------------------
echo ""
echo "1. Health check"
STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/health")
assert_status "GET /health" 200 "$STATUS"

# ----------------------------------------------------------
echo ""
echo "2. Login as seeded admin"

RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"dkberktas+admin@gmail.com","password":"change-me-in-production"}')
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "Login as admin" 200 "$STATUS"
ADMIN_TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "  Admin token: ${ADMIN_TOKEN:0:20}..."

# ----------------------------------------------------------
echo ""
echo "3. Admin creates attorney accounts"

RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/admin/attorneys" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"dkberktas+alice@gmail.com","password":"attorney123"}')
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "Admin creates alice" 201 "$STATUS"
ALICE_ROLE=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['role'])")
assert_field "Alice's role" "ATTORNEY" "$ALICE_ROLE"

RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/admin/attorneys" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"dkberktas+bob@gmail.com","password":"attorney456"}')
STATUS=$(echo "$RESP" | tail -1)
assert_status "Admin creates bob" 201 "$STATUS"

# Duplicate should fail
RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/admin/attorneys" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"dkberktas+alice@gmail.com","password":"attorney123"}')
STATUS=$(echo "$RESP" | tail -1)
assert_status "Duplicate attorney rejected" 400 "$STATUS"

# ----------------------------------------------------------
echo ""
echo "4. Login as attorney Alice"

RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"dkberktas+alice@gmail.com","password":"attorney123"}')
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "Login as Alice" 200 "$STATUS"
TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "  Attorney token: ${TOKEN:0:20}..."

# Wrong password
RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"dkberktas+alice@gmail.com","password":"wrong"}')
STATUS=$(echo "$RESP" | tail -1)
assert_status "Wrong password rejected" 401 "$STATUS"

# ----------------------------------------------------------
echo ""
echo "5. Attorney cannot access admin endpoints"

RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/admin/attorneys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"dkberktas+sneaky@gmail.com","password":"x"}')
STATUS=$(echo "$RESP" | tail -1)
assert_status "Attorney create attorney blocked" 403 "$STATUS"

RESP=$(curl -s -w '\n%{http_code}' "$API/admin/users" \
  -H "Authorization: Bearer $TOKEN")
STATUS=$(echo "$RESP" | tail -1)
assert_status "Attorney list users blocked" 403 "$STATUS"

# ----------------------------------------------------------
echo ""
echo "6. Admin can list users"

RESP=$(curl -s -w '\n%{http_code}' "$API/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "Admin list users" 200 "$STATUS"
USER_COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "  Users: $USER_COUNT"

# ----------------------------------------------------------
echo ""
echo "7. Create leads (public, no auth)"

TMPFILE=$(mktemp /tmp/resume_XXXXXX.pdf)
echo "%PDF-1.4 fake resume content" > "$TMPFILE"

RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/leads" \
  -F "first_name=Jane" \
  -F "last_name=Doe" \
  -F "email=dkberktas+jane@gmail.com" \
  -F "resume=@$TMPFILE;type=application/pdf")
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "Create lead Jane Doe" 201 "$STATUS"
LEAD1_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
LEAD1_STATE=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
assert_field "Jane's initial state" "PENDING" "$LEAD1_STATE"
echo "  Lead ID: $LEAD1_ID"

RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/leads" \
  -F "first_name=John" \
  -F "last_name=Smith" \
  -F "email=dkberktas+john@gmail.com" \
  -F "resume=@$TMPFILE;type=application/pdf")
STATUS=$(echo "$RESP" | tail -1)
assert_status "Create lead John Smith" 201 "$STATUS"

RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/leads" \
  -F "first_name=Maria" \
  -F "last_name=Garcia" \
  -F "email=dkberktas+maria@gmail.com" \
  -F "resume=@$TMPFILE;type=application/pdf")
STATUS=$(echo "$RESP" | tail -1)
assert_status "Create lead Maria Garcia" 201 "$STATUS"

rm -f "$TMPFILE"

# Invalid file type
TXTFILE=$(mktemp /tmp/resume_XXXXXX.txt)
echo "plain text" > "$TXTFILE"
RESP=$(curl -s -w '\n%{http_code}' -X POST "$API/leads" \
  -F "first_name=Bad" \
  -F "last_name=File" \
  -F "email=dkberktas+bad@gmail.com" \
  -F "resume=@$TXTFILE;type=text/plain")
STATUS=$(echo "$RESP" | tail -1)
assert_status "Reject .txt upload" 400 "$STATUS"
rm -f "$TXTFILE"

# ----------------------------------------------------------
echo ""
echo "8. List leads (requires auth)"

RESP=$(curl -s -w '\n%{http_code}' "$API/leads")
STATUS=$(echo "$RESP" | tail -1)
assert_status "List leads without auth rejected" 403 "$STATUS"

RESP=$(curl -s -w '\n%{http_code}' "$API/leads" \
  -H "Authorization: Bearer $TOKEN")
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "List leads with auth" 200 "$STATUS"
COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "  Leads returned: $COUNT"

# ----------------------------------------------------------
echo ""
echo "9. Get single lead"

RESP=$(curl -s -w '\n%{http_code}' "$API/leads/$LEAD1_ID" \
  -H "Authorization: Bearer $TOKEN")
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "Get lead by ID" 200 "$STATUS"
NAME=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['first_name'],d['last_name'])")
assert_field "Lead name" "Jane Doe" "$NAME"

# ----------------------------------------------------------
echo ""
echo "10. Update lead state → REACHED_OUT"

RESP=$(curl -s -w '\n%{http_code}' -X PATCH "$API/leads/$LEAD1_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state":"REACHED_OUT"}')
STATUS=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "Mark Jane as REACHED_OUT" 200 "$STATUS"
NEW_STATE=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
assert_field "Updated state" "REACHED_OUT" "$NEW_STATE"

# ----------------------------------------------------------
echo ""
echo "11. Verify state cannot revert"

RESP=$(curl -s -w '\n%{http_code}' -X PATCH "$API/leads/$LEAD1_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state":"PENDING"}')
STATUS=$(echo "$RESP" | tail -1)
assert_status "Revert to PENDING rejected" 400 "$STATUS"

# ----------------------------------------------------------
echo ""
echo "12. Admin deletes attorney Bob"

BOB_ID=$(echo "$BODY" | python3 -c "
import sys, json
# Get Bob's ID from user list
" 2>/dev/null || true)

RESP=$(curl -s -w '\n%{http_code}' "$API/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
BODY=$(echo "$RESP" | sed '$d')
BOB_ID=$(echo "$BODY" | python3 -c "
import sys, json
users = json.load(sys.stdin)
bob = next(u for u in users if u['email'] == 'dkberktas+bob@gmail.com')
print(bob['id'])
")

RESP=$(curl -s -w '\n%{http_code}' -X DELETE "$API/admin/users/$BOB_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
STATUS=$(echo "$RESP" | tail -1)
assert_status "Admin deletes Bob" 204 "$STATUS"

# Verify Bob is gone
RESP=$(curl -s -w '\n%{http_code}' "$API/admin/users/$BOB_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
STATUS=$(echo "$RESP" | tail -1)
assert_status "Bob no longer exists" 404 "$STATUS"

# ----------------------------------------------------------
echo ""
echo "================================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "================================================"
echo ""

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
