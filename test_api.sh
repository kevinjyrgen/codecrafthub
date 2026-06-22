#!/usr/bin/env bash
# CodeCraftHub API — automated test suite
# Usage: start the server (python app.py), then:  bash test_api.sh
# Requires: curl, python3

BASE="http://localhost:5001"
PASS=0
FAIL=0

# check <label> <expected_code> <actual_code>
check() {
  if [ "$2" = "$3" ]; then
    echo "  PASS  $1  (HTTP $3)"
    PASS=$((PASS+1))
  else
    echo "  FAIL  $1  (expected $2, got $3)"
    FAIL=$((FAIL+1))
  fi
}

# code <curl args...>  -> prints HTTP status only
code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

echo "== Resetting data =="
# Wipe any existing courses so IDs start at 1
for id in $(curl -s "$BASE/api/courses" | python3 -c "import sys,json;print(' '.join(str(c['id']) for c in json.load(sys.stdin)['data']))" 2>/dev/null); do
  curl -s -X DELETE "$BASE/api/courses/$id" >/dev/null
done

echo "== Health =="
check "health up" 200 "$(code $BASE/api/health)"

echo "== Create (valid) =="
check "create #1" 201 "$(code -X POST $BASE/api/courses -H 'Content-Type: application/json' -d '{"name":"Python Basics","description":"Learn Python fundamentals","target_date":"2025-12-31","status":"Not Started"}')"
check "create #2" 201 "$(code -X POST $BASE/api/courses -H 'Content-Type: application/json' -d '{"name":"Core ML","description":"On-device ML","target_date":"2026-03-01","status":"In Progress"}')"

echo "== Read =="
check "list all" 200 "$(code $BASE/api/courses)"
check "get id 1" 200 "$(code $BASE/api/courses/1)"
check "get id 999 (not found)" 404 "$(code $BASE/api/courses/999)"
check "search q=core" 200 "$(code $BASE/api/courses/search?q=core)"
check "stats" 200 "$(code $BASE/api/courses/stats)"

echo "== Update =="
check "update id 1 status" 200 "$(code -X PUT $BASE/api/courses/1 -H 'Content-Type: application/json' -d '{"status":"Completed"}')"
check "update id 999 (not found)" 404 "$(code -X PUT $BASE/api/courses/999 -H 'Content-Type: application/json' -d '{"status":"Completed"}')"

echo "== Validation errors =="
check "missing name" 422 "$(code -X POST $BASE/api/courses -H 'Content-Type: application/json' -d '{"description":"no name"}')"
check "invalid status" 422 "$(code -X POST $BASE/api/courses -H 'Content-Type: application/json' -d '{"name":"X","status":"Invalid Status"}')"
check "invalid date" 422 "$(code -X POST $BASE/api/courses -H 'Content-Type: application/json' -d '{"name":"X","target_date":"31-12-2025"}')"
check "empty name" 422 "$(code -X POST $BASE/api/courses -H 'Content-Type: application/json' -d '{"name":"   "}')"
check "malformed JSON" 400 "$(code -X POST $BASE/api/courses -H 'Content-Type: application/json' -d '{not json}')"
check "PUT no valid fields" 422 "$(code -X PUT $BASE/api/courses/1 -H 'Content-Type: application/json' -d '{"unknown":"field"}')"

echo "== Delete =="
check "delete id 1" 200 "$(code -X DELETE $BASE/api/courses/1)"
check "delete id 1 again (not found)" 404 "$(code -X DELETE $BASE/api/courses/1)"

echo
echo "================================"
echo "  Passed: $PASS   Failed: $FAIL"
echo "================================"
[ "$FAIL" -eq 0 ]
