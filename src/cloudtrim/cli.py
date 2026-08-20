"""Interface en ligne de commande : génère un CUR synthétique, l'ingère dans DuckDB,
et affiche les premières agrégations."""

from __future__ import annotations

import argparse

from cloudtrim.adapters.csv_writer import write_cur_csv
from cloudtrim.adapters.duckdb_repository import DuckDBRepository
from cloudtrim.domain.generator import generate_cur


def cmd_generate(args: argparse.Namespace) -> None:
    """Génère un CSV CUR synthétique."""
    items = generate_cur(days=args.days, num_resources=args.resources, seed=args.seed)
    path = write_cur_csv(items, args.out)
    total = sum(i.unblended_cost for i in items)
    print(f"{len(items)} lignes écrites dans {path} (coût total simulé : {total:,.2f} $).")


def cmd_ingest(args: argparse.Namespace) -> None:
    """Ingère un CSV CUR dans DuckDB et affiche les agrégations."""
    repo = DuckDBRepository(db_path=args.db)
    count = repo.load_cur_csv(args.csv)
    print(f"{count} lignes chargées dans {args.db}.")

    print("\n=== Coût par service (top 5) ===")
    for row in repo.cost_by_product()[:5]:
        print(f"  {row['label']}: {row['total_cost']:,.2f} $")

    print("\n=== Coût par région ===")
    for row in repo.cost_by_region():
        print(f"  {row['label']}: {row['total_cost']:,.2f} $")

    print("\n=== Coût par équipe (top 5) ===")
    for row in repo.cost_by_team()[:5]:
        print(f"  {row['label']}: {row['total_cost']:,.2f} $")

    print("\n=== Évolution journalière (5 premiers jours) ===")
    for row in repo.daily_cost()[:5]:
        print(f"  {row['day']}: {row['daily_cost']:,.2f} $")

    repo.close()

def cmd_serve(args: argparse.Namespace) -> None:
    """Lance le serveur API + dashboard."""
    import uvicorn

    from cloudtrim.api.dependencies import set_db_path

    set_db_path(args.db)
    print(f"🚀 CloudTrim API + Dashboard démarré sur http://localhost:{args.port}")
    print(f"📊 Dashboard : http://localhost:{args.port}/")
    print(f"📚 API Docs : http://localhost:{args.port}/docs")
    uvicorn.run("cloudtrim.api.app:app", host=args.host, port=args.port, reload=args.reload)


def cmd_analyze(args: argparse.Namespace) -> None:
    """Analyse les données CUR et détecte le gaspillage et les anomalies."""
    from cloudtrim.domain.analyzer import (
        analyze_orphan_resources,
        analyze_untagged_resources,
        detect_cost_anomalies,
    )

    repo = DuckDBRepository(db_path=args.db)

    print("=== Analyse des dépenses non taguées ===")
    untagged_costs = repo.get_untagged_resources_daily_costs()
    untagged_findings = analyze_untagged_resources(untagged_costs, recovery_rate=0.4)

    if not untagged_findings:
        print("  Aucune dépense non taguée détectée.")
    else:
        total_lower = sum(f.details["adjusted_savings_range"][0] for f in untagged_findings)
        total_upper = sum(f.details["adjusted_savings_range"][1] for f in untagged_findings)
        print(f"  {len(untagged_findings)} ressources non taguées détectées.")
        print(f"  Économie potentielle (40% récupérable) : {total_lower:,.2f} $ à {total_upper:,.2f} $")
        print(f"  (avec {untagged_findings[0].estimate.confidence_level*100:.0f}% de confiance)")

        for finding in untagged_findings[:5]:
            low, high = finding.details["adjusted_savings_range"]
            print(f"    - {finding.resource_id}: {low:,.2f} $ à {high:,.2f} $")

    print("\n=== Analyse des ressources orphelines ===")
    orphan_costs = repo.get_orphan_resources_daily_costs()
    orphan_findings = analyze_orphan_resources(orphan_costs)

    if not orphan_findings:
        print("  Aucune ressource orpheline détectée.")
    else:
        total_lower = sum(f.estimate.confidence_interval_total[0] for f in orphan_findings)
        total_upper = sum(f.estimate.confidence_interval_total[1] for f in orphan_findings)
        print(f"  {len(orphan_findings)} ressources orphelines détectées.")
        print(f"  Économie potentielle (100% récupérable) : {total_lower:,.2f} $ à {total_upper:,.2f} $")
        print(f"  (avec {orphan_findings[0].estimate.confidence_level*100:.0f}% de confiance)")

        for finding in orphan_findings[:5]:
            low, high = finding.estimate.confidence_interval_total
            print(f"    - {finding.resource_id}: {low:,.2f} $ à {high:,.2f} $")

    print("\n=== Détection d'anomalies de coût ===")
    all_costs = repo.get_all_resources_daily_costs()
    anomalies = detect_cost_anomalies(all_costs, threshold=3.0)

    if not anomalies:
        print("  Aucune anomalie détectée.")
    else:
        critical = [a for a in anomalies if a.severity == "critical"]
        moderate = [a for a in anomalies if a.severity == "moderate"]
        print(f"  {len(anomalies)} anomalies détectées ({len(critical)} critiques, {len(moderate)} modérées).")

        for anomaly in anomalies[:10]:  # top 10
            severity_icon = "🔴" if anomaly.severity == "critical" else "🟡"
            print(
                f"    {severity_icon} {anomaly.resource_id} le {anomaly.day}: "
                f"{anomaly.cost:,.2f} $ (médiane: {anomaly.median_cost:,.2f} $, Z-score: {anomaly.z_score:.2f})"
            )

    repo.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudTrim : moteur FinOps sur CUR AWS.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sous-commande : generate
    gen_parser = subparsers.add_parser("generate", help="Génère un CUR synthétique.")
    gen_parser.add_argument("--days", type=int, default=30, help="Nombre de jours (défaut 30).")
    gen_parser.add_argument("--resources", type=int, default=20, help="Nombre de ressources.")
    gen_parser.add_argument("--seed", type=int, default=42, help="Graine de reproductibilité.")
    gen_parser.add_argument("--out", default="data/sample_cur.csv", help="Chemin du CSV de sortie.")
    gen_parser.set_defaults(func=cmd_generate)

    # Sous-commande : serve
    serve_parser = subparsers.add_parser("serve", help="Lance le serveur API + dashboard.")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Hôte (défaut 0.0.0.0).")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (défaut 8000).")
    serve_parser.add_argument("--db", default="data/cloudtrim.duckdb", help="Chemin du fichier DuckDB.")
    serve_parser.add_argument("--reload", action="store_true", help="Rechargement automatique (dev).")
    serve_parser.set_defaults(func=cmd_serve)

    # Sous-commande : ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingère un CSV CUR dans DuckDB.")
    ingest_parser.add_argument("--csv", default="data/sample_cur.csv", help="Chemin du CSV CUR.")
    ingest_parser.add_argument("--db", default="data/cloudtrim.duckdb", help="Chemin du fichier DuckDB.")
    ingest_parser.set_defaults(func=cmd_ingest)

    # Sous-commande : analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyse le gaspillage et estime les économies.")
    analyze_parser.add_argument("--db", default="data/cloudtrim.duckdb", help="Chemin du fichier DuckDB.")
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    args.func(args)

     


if __name__ == "__main__":
    main()