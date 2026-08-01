"""
Grants a service account dataset-level BigQuery access via the stable ACL
mechanism (Dataset.access_entries), not `bq add-iam-policy-binding` -- that
command requires a preview feature ("conditional/IAM-native dataset bindings")
that needs allowlisting and isn't enabled on this project. access_entries is
the same mechanism the BigQuery UI's "Sharing > Permissions" panel uses and
has been stable for years.

Usage:
    python3 grant_dataset_access.py <project> <dataset> <role> <service_account_email>

Idempotent: safe to re-run, skips if the entry already exists.
"""

import sys

from google.cloud import bigquery


def main() -> None:
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    project, dataset_id, role, sa_email = sys.argv[1:5]

    client = bigquery.Client(project=project)
    dataset = client.get_dataset(f"{project}.{dataset_id}")

    entries = list(dataset.access_entries)
    new_entry = bigquery.AccessEntry(role=role, entity_type="userByEmail", entity_id=sa_email)

    if new_entry in entries:
        print(f"  {dataset_id}: {sa_email} already has {role} -- skipping")
        return

    entries.append(new_entry)
    dataset.access_entries = entries
    client.update_dataset(dataset, ["access_entries"])
    print(f"  {dataset_id}: granted {role} to {sa_email}")


if __name__ == "__main__":
    main()
