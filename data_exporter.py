import os
import csv
import json
import threading


FIELD_ORDER = [
    "business_name",
    "registration_id",
    "status",
    "filing_date",
    "agent_name",
    "agent_address",
    "agent_email",
]

CSV_HEADERS = {
    "business_name": "Business Name",
    "registration_id": "Registration ID",
    "status": "Status",
    "filing_date": "Filing Date",
    "agent_name": "Agent Name",
    "agent_address": "Agent Address",
    "agent_email": "Agent Email",
}


class DataExporter:

    def __init__(self, query, output_dir="output"):
        self.query = query
        self.output_dir = output_dir
        self.results = []
        self.seen_ids = set()
        self._lock = threading.Lock()

        os.makedirs(self.output_dir, exist_ok=True)

    @property
    def json_path(self):
        return os.path.join(self.output_dir, f"{self.query}.json")

    @property
    def csv_path(self):
        return os.path.join(self.output_dir, f"{self.query}.csv")

    def add_results(self, api_results):
        new_count = 0
        with self._lock:
            for item in api_results:
                reg_id = item.get("registrationId")
                if reg_id in self.seen_ids:
                    continue

                agent = item.get("agent", {})
                record = {
                    "business_name": item.get("businessName", ""),
                    "registration_id": reg_id,
                    "status": item.get("status", ""),
                    "filing_date": item.get("filingDate", ""),
                    "agent_name": agent.get("name", ""),
                    "agent_address": agent.get("address", ""),
                    "agent_email": agent.get("email", ""),
                }
                self.results.append(record)
                self.seen_ids.add(reg_id)
                new_count += 1

        return new_count

    def save(self):
        self._save_json()
        self._save_csv()
        self._print_summary()

    def _save_json(self):
        tmp_path = self.json_path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.json_path)
        print(f"[EXPORT] JSON saved: {self.json_path}")

    def _save_csv(self):
        tmp_path = self.csv_path + ".tmp"
        display_headers = [CSV_HEADERS[f] for f in FIELD_ORDER]
        with open(tmp_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(display_headers)
            for record in self.results:
                writer.writerow([record.get(f, "") for f in FIELD_ORDER])
        os.replace(tmp_path, self.csv_path)
        print(f"[EXPORT] CSV saved: {self.csv_path}")

    def _print_summary(self):
        total = len(self.results)
        unique_ids = len(self.seen_ids)
        statuses = {}
        for r in self.results:
            s = r.get("status", "Unknown")
            statuses[s] = statuses.get(s, 0) + 1

        print(f"\n{'='*50}")
        print(f"  EXPORT SUMMARY")
        print(f"{'='*50}")
        print(f"  Query:            {self.query}")
        print(f"  Total Records:    {total}")
        print(f"  Unique IDs:       {unique_ids}")
        print(f"  Duplicates:       {total - unique_ids}")
        print(f"  Status Breakdown:")
        for status, count in sorted(statuses.items()):
            print(f"    {status}: {count}")
        print(f"  JSON: {self.json_path}")
        print(f"  CSV:  {self.csv_path}")
        print(f"{'='*50}\n")

    def verify_integrity(self):
        errors = []

        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            if len(json_data) != len(self.results):
                errors.append(
                    f"JSON record count mismatch: file={len(json_data)}, "
                    f"memory={len(self.results)}"
                )
        except Exception as e:
            errors.append(f"JSON validation failed: {e}")

        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                csv_rows = list(reader)
            if len(csv_rows) != len(self.results):
                errors.append(
                    f"CSV record count mismatch: file={len(csv_rows)}, "
                    f"memory={len(self.results)}"
                )
            expected_headers = [CSV_HEADERS[f] for f in FIELD_ORDER]
            if reader.fieldnames != expected_headers:
                errors.append(
                    f"CSV header mismatch: expected {expected_headers}, "
                    f"got {reader.fieldnames}"
                )
        except Exception as e:
            errors.append(f"CSV validation failed: {e}")

        if errors:
            print("[EXPORT] Integrity check FAILED:")
            for err in errors:
                print(f"  - {err}")
            return False

        print("[EXPORT] Integrity check PASSED — JSON and CSV are consistent.")
        return True
