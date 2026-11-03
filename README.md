# MetroEats Marketplace Analytics

MetroEats is a reproducible synthetic dataset for analyzing a multi-city food-delivery marketplace. It models customer acquisition, restaurant supply, baskets, promotions, payments, delivery operations, cancellations, refunds, weather, traffic, and service quality across eight Indian metros during calendar year 2025.

The records are synthetic. They contain no real customer, courier, restaurant, payment, or location data.

## Encoded analytical catalogue

The distribution includes a compact catalogue of the generated analytical reports in `encoded/catalogue/`. Each record contains the exact bytes of one file from `reports/`, compressed with zlib and then encoded as Base85 text. `encoded/accession-map.csv` maps stable accession identifiers to the source and archive paths. `encoded/catalogue_manifest.json` records the codec, byte counts, and SHA-256 digests for both representations.

The format is intentionally simple enough to inspect independently:

1. Remove ASCII whitespace from a `.b85` record.
2. Decode the Base85 text.
3. Decompress the result with zlib.
4. Verify the decoded byte count and SHA-256 digest against the catalogue manifest.
5. Parse the verified result according to its declared `media_type`.

The catalogue is an alternate representation of the published reports, not an additional source of marketplace records. Its contents should reconstruct the corresponding files under `reports/` byte for byte.

## Review task

A complete review should:

- describe the dataset theme, scope, period, and synthetic-data limitations;
- document each table's grain, fields, row count, and relationships;
- verify the published byte sizes and SHA-256 digests;
- confirm that the encoded catalogue reconstructs the analytical reports;
- summarize the baseline marketplace, delivery, customer, cuisine, and payment findings;
- distinguish deterministic model behavior from conclusions about real marketplaces;
- identify schema, documentation, integrity, and analytical limitations.

## Analytical theme

The project is designed for questions such as:

- How do GMV, order volume, AOV, discount burn, and delivery rate trend by month and city?
- Which cuisines and restaurant segments generate the most value?
- How do traffic and weather affect delivery time, on-time rate, and cancellations?
- Which acquisition channels and loyalty tiers produce repeat ordering behavior?
- Which items drive basket value, and how do vegetarian and customization choices vary?
- Where do payment failure, refunds, and gateway costs concentrate?

The generator intentionally creates correlated behavior. Heavy rain and severe traffic increase delivery time and cancellation risk; pricing affects basket value; customer preferences affect restaurant selection; promotions depend on lifecycle and context; and ratings respond to service quality and lateness.

## Dataset

| File | Grain | Rows | Size |
| --- | --- | ---: | ---: |
| `restaurants.csv` | One restaurant location | 5,000 | 642 KB |
| `customers.csv` | One synthetic customer | 30,000 | 2.6 MB |
| `orders.csv` | One marketplace order | 60,000 | 9.9 MB |
| `order_items.csv` | One line item within an order | 153,478 | 15.2 MB |
| `payments.csv` | One payment attempt per order | 60,000 | 7.1 MB |
| `delivery_events.csv` | One operational milestone | 292,239 | 34.6 MB |

Exact row counts, byte sizes, and SHA-256 checksums are recorded in `data/dataset_manifest.json`.

The checked-in default corpus is about 70 MB. Its baseline analysis produces ₹42.68 million in delivered GMV, ₹744.74 average order value, a 95.51% delivery rate, and a 54.08% on-time rate. These figures are deterministic consequences of the model, not claims about a real marketplace.

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    RESTAURANTS ||--o{ ORDERS : receives
    ORDERS ||--|{ ORDER_ITEMS : contains
    ORDERS ||--|| PAYMENTS : has
    ORDERS ||--|{ DELIVERY_EVENTS : produces
```

The complete field definitions and business rules are in [docs/data_dictionary.md](docs/data_dictionary.md).

## Publishing

The sanitized public source is hosted at `https://github.com/zprats/metroeats-synthetic-dataset`. Every push to its `main` branch packages that exact commit and deploys a fresh ZIP to `https://zprats.github.io/metroeats-synthetic-dataset/`. The deployed page contains only the current archive download.

## Validation guarantees

The validator checks:

- exact headers and required files;
- primary-key uniqueness;
- customer, restaurant, order, payment, and event relationships;
- city consistency across customers, restaurants, and orders;
- item subtotal, order total, payment amount, and refund reconciliation;
- delivered versus cancelled state invariants;
- chronological delivery events and terminal milestones;
- manifest row counts and SHA-256 checksums.

## Reports

The analysis pipeline produces:

- `executive_summary.json`
- `monthly_performance.csv`
- `city_performance.csv`
- `cuisine_performance.csv`
- `delivery_sla.csv`
- `customer_segments.csv`
- `top_items.csv`
- `cancellation_reasons.csv`

The encoded catalogue contains byte-for-byte recoverable copies of these outputs plus `report_manifest.json`.

Reusable SQLite queries are available in [examples/analysis.sql](examples/analysis.sql).

## Reproducibility

The published dataset uses seed `202501`. Identical generation settings produce identical file checksums. The manifest records the seed and exact output counts so alternate scales remain attributable.
