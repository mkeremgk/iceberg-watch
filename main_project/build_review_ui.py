"""Build an offline review form. Decisions leave the browser only via CSV download."""
import csv
import json
from map_io import DIRECTORY
from review_provenance import verify_binding
from review_associations import validate_reviews


def main():
    verify_binding(DIRECTORY)
    folder = DIRECTORY/'association_review'
    records = json.loads((folder/'diagnostics.json').read_text())
    with (folder/'human_review.csv').open(newline='') as handle:
        reviewed = validate_reviews(records, list(csv.DictReader(handle)))['links']
    payload = json.dumps(reviewed).replace('<', '\\u003c')
    template = Path(__file__).with_name('review_ui.html').read_text()
    (folder/'review.html').write_text(template.replace('__RECORDS__', payload))
    print('Offline review:', folder/'review.html')


from pathlib import Path
if __name__ == '__main__':
    main()
