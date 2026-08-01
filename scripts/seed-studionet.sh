#!/bin/bash
# Seed script for ProofFund on StudioNet
# Uses genlayer CLI for transactions

CONTRACT="0x8bf3c1C1D1E7f5ba14C6Ab9C58486b92A03ECED4"
NOW=$(date +%s)
DAY=86400

echo "=== Seeding ProofFund on StudioNet ==="
echo "Contract: $CONTRACT"
echo ""

# Project 1: Open Climate Data Atlas
echo "📦 Creating Project 1: Open Climate Data Atlas"
genlayer write $CONTRACT create_project \
  --args "Open Climate Data Atlas" "Climate" \
  "A comprehensive, publicly accessible atlas of climate datasets with interactive visualizations and API access for researchers worldwide." \
  "This project builds an open-access climate data platform that aggregates satellite observations, ground station measurements, and model outputs into a unified, queryable atlas. The platform will provide interactive visualizations, standardized APIs, and downloadable datasets to accelerate climate research and public understanding of environmental change." \
  "https://github.com/example/climate-atlas" "" \
  "5000000000000000000" "$((NOW + 90*DAY))" \
  "Data pipeline and infrastructure" "2000000000000000000" "$((NOW + 30*DAY))"
sleep 2

echo "  → Adding milestones..."
genlayer write $CONTRACT add_milestone --args "PF-0001" "Data ingestion pipeline operational" \
  "A working ETL pipeline that ingests at least 3 public climate datasets (NOAA, ERA5, MODIS) with automated quality checks and storage in a queryable format." \
  "2000000000000000000" "$((NOW + 30*DAY))"
sleep 2

genlayer write $CONTRACT add_milestone --args "PF-0001" "Interactive atlas with public API" \
  "A web-based interactive atlas with map visualizations, time-series charts, and filtering. A REST API with endpoints for dataset queries and data downloads." \
  "3000000000000000000" "$((NOW + 60*DAY))"
sleep 2

echo "  → Funding project..."
genlayer write $CONTRACT fund_project --args "PF-0001" --value 5000000000000000000
sleep 2

# Project 2: Civic Transparency Ledger
echo "📦 Creating Project 2: Civic Transparency Ledger"
genlayer write $CONTRACT create_project \
  --args "Civic Transparency Ledger" "Governance" \
  "An open platform tracking municipal spending with searchable databases, trend analysis, and citizen alert systems for anomalous expenditures." \
  "This project creates a transparent, auditable ledger of municipal government spending that aggregates public budget data, procurement records, and expenditure reports. The platform will provide searchable databases, trend analysis tools, and automated alert systems for citizens and journalists." \
  "https://github.com/example/civic-ledger" "" \
  "3000000000000000000" "$((NOW + 60*DAY))" \
  "Initial development" "3000000000000000000" "$((NOW + 45*DAY))"
sleep 2

echo "  → Adding milestones..."
genlayer write $CONTRACT add_milestone --args "PF-0002" "Data aggregation and search" \
  "A system that aggregates spending data from at least 5 municipal sources with full-text search, category filtering, and date range queries." \
  "1500000000000000000" "$((NOW + 30*DAY))"
sleep 2

genlayer write $CONTRACT add_milestone --args "PF-0002" "Analytics and alert system" \
  "Trend analysis dashboards showing spending patterns over time. An automated alert system that flags anomalous expenditures with email notifications." \
  "1500000000000000000" "$((NOW + 45*DAY))"
sleep 2

echo "  → Funding project..."
genlayer write $CONTRACT fund_project --args "PF-0002" --value 3000000000000000000
sleep 2

# Project 3: Open Source Security Audit Toolkit
echo "📦 Creating Project 3: Open Source Security Audit Toolkit"
genlayer write $CONTRACT create_project \
  --args "Open Source Security Audit Toolkit" "Security" \
  "A comprehensive suite of automated security scanning tools for open source projects with vulnerability detection, dependency analysis, and compliance reporting." \
  "This project develops an integrated security audit toolkit that combines static analysis, dependency scanning, and compliance checking into a unified platform. All tools will be released as open source with extensive documentation." \
  "https://github.com/example/security-toolkit" "" \
  "4000000000000000000" "$((NOW + 75*DAY))" \
  "Core scanning engine" "4000000000000000000" "$((NOW + 60*DAY))"
sleep 2

echo "  → Adding milestones..."
genlayer write $CONTRACT add_milestone --args "PF-0003" "Vulnerability scanner MVP" \
  "A command-line tool that scans repositories for known vulnerabilities (CVEs) in dependencies, with support for npm, pip, and Go modules." \
  "2000000000000000000" "$((NOW + 30*DAY))"
sleep 2

genlayer write $CONTRACT add_milestone --args "PF-0003" "Compliance and license checker" \
  "A license compliance analyzer that identifies all dependencies and their licenses, flags incompatible license combinations, and generates compliance reports." \
  "2000000000000000000" "$((NOW + 60*DAY))"
sleep 2

echo "  → Funding project..."
genlayer write $CONTRACT fund_project --args "PF-0003" --value 4000000000000000000
sleep 2

# Project 4: Decentralized Research Archive
echo "📦 Creating Project 4: Decentralized Research Archive"
genlayer write $CONTRACT create_project \
  --args "Decentralized Research Archive" "Research" \
  "A peer-to-peer archive for scientific publications with persistent identifiers, version control, and citation tracking independent of traditional publishers." \
  "This project builds a decentralized archive system for scientific research that operates independently of traditional publishers. Using peer-to-peer storage and blockchain-based provenance." \
  "https://github.com/example/research-archive" "" \
  "6000000000000000000" "$((NOW + 120*DAY))" \
  "Storage and identifier layer" "3000000000000000000" "$((NOW + 45*DAY))"
sleep 2

echo "  → Adding tranche..."
genlayer write $CONTRACT add_funding_tranche --args "PF-0004" "Discovery and citation system" \
  "3000000000000000000" "$((NOW + 90*DAY))"
sleep 2

echo "  → Adding milestones..."
genlayer write $CONTRACT add_milestone --args "PF-0004" "P2P storage with persistent IDs" \
  "A working peer-to-peer storage system that accepts research documents and assigns persistent, content-addressed identifiers." \
  "3000000000000000000" "$((NOW + 45*DAY))"
sleep 2

genlayer write $CONTRACT add_milestone --args "PF-0004" "Search and citation tracking" \
  "A web-based discovery interface with full-text search, metadata filtering, and author profiles. A citation tracking system that monitors references." \
  "3000000000000000000" "$((NOW + 90*DAY))"
sleep 2

echo "  → Funding project..."
genlayer write $CONTRACT fund_project --args "PF-0004" --value 6000000000000000000
sleep 2

# Project 5: Public Health Data Commons
echo "📦 Creating Project 5: Public Health Data Commons"
genlayer write $CONTRACT create_project \
  --args "Public Health Data Commons" "Health" \
  "An open platform aggregating public health datasets with privacy-preserving analytics, epidemiological modeling tools, and policy impact tracking." \
  "This project creates a unified platform for public health data that aggregates epidemiological datasets, demographic statistics, and health outcome metrics. Privacy-preserving analytics tools and epidemiological modeling capabilities." \
  "https://github.com/example/health-commons" "" \
  "5000000000000000000" "$((NOW + 100*DAY))" \
  "Data integration layer" "2500000000000000000" "$((NOW + 40*DAY))"
sleep 2

echo "  → Adding tranche..."
genlayer write $CONTRACT add_funding_tranche --args "PF-0005" "Analytics and modeling tools" \
  "2500000000000000000" "$((NOW + 80*DAY))"
sleep 2

echo "  → Adding milestones..."
genlayer write $CONTRACT add_milestone --args "PF-0005" "Multi-source data integration" \
  "A system that integrates health data from at least 4 public sources with standardized schemas, quality validation, and temporal alignment." \
  "2500000000000000000" "$((NOW + 40*DAY))"
sleep 2

genlayer write $CONTRACT add_milestone --args "PF-0005" "Privacy-preserving analytics suite" \
  "A suite of analytics tools that support epidemiological modeling with differential privacy guarantees. Includes visualization dashboards for health metrics." \
  "2500000000000000000" "$((NOW + 80*DAY))"
sleep 2

echo "  → Funding project..."
genlayer write $CONTRACT fund_project --args "PF-0005" --value 5000000000000000000
sleep 2

echo ""
echo "=== Submitting evidence for first milestones ==="

genlayer write $CONTRACT submit_evidence --args "PF-0001" "PF-0001-M1" \
  "https://github.com/example/climate-atlas" \
  "Initial evidence for data ingestion pipeline. All acceptance criteria have been addressed with comprehensive documentation and working implementations."
sleep 2

genlayer write $CONTRACT submit_evidence --args "PF-0002" "PF-0002-M1" \
  "https://github.com/example/civic-ledger" \
  "Data aggregation system operational with 5 municipal sources integrated. Full-text search and filtering implemented."
sleep 2

genlayer write $CONTRACT submit_evidence --args "PF-0003" "PF-0003-M1" \
  "https://github.com/example/security-toolkit" \
  "Vulnerability scanner MVP complete with support for npm, pip, and Go modules. Comprehensive test suite included."
sleep 2

echo ""
echo "=== Creating governance proposals ==="

genlayer write $CONTRACT create_proposal --args "PF-0001" \
  "Extend project timeline for quality assurance" \
  "The current deadline may be tight for comprehensive testing. Extending by 30 days would allow more thorough validation." \
  "EXTEND_DEADLINE" "$((NOW + 120*DAY))" "$((NOW + 7*DAY))"
sleep 2

genlayer write $CONTRACT vote_proposal --args "PF-0001-G1" true
sleep 2

echo ""
echo "=== Seed complete ==="
echo "Total projects: 5"
echo "Total funded: 23 GEN"
echo "Contract: $CONTRACT"
