"""
Benchmark documents: URL configs and evaluation tasks.

Each entry has:
  id        — used as fixture filename (benchmark/fixtures/<id>.doctags)
  title     — human-readable label
  md_url    — annotated Markdown URL (UTF-8 BOM, YAML frontmatter)
  html_url  — HTML URL for content-negotiation fetch
  tasks     — list of evaluation tasks (id, category, question, ground_truth)
"""

DOCUMENTS = [
    {
        "id": "fleet_cmd",
        "title": "Fleet Agent Command Reference",
        "md_url": (
            "https://www.elastic.co/docs/reference/fleet/agent-command-reference.md"
        ),
        "html_url": (
            "https://www.elastic.co/docs/reference/fleet/agent-command-reference"
        ),
        "tasks": [
            {
                "id": "diagnostics_synopsis",
                "category": "code_extraction",
                "question": (
                    "What is the full command synopsis for `elastic-agent diagnostics`, "
                    "listing all optional flags?"
                ),
                "ground_truth": (
                    "elastic-agent diagnostics [--file <string>] [--cpu-profile] "
                    "[--exclude-events] [--help] [global-flags]"
                ),
            },
            {
                "id": "diagnostics_security",
                "category": "factual_retrieval",
                "question": (
                    "What security warning does the documentation give about the "
                    "output archive produced by the diagnostics command?"
                ),
                "ground_truth": (
                    "Credentials may not be redacted in the archive; they may appear "
                    "in plain text in the configuration or policy files inside the archive."
                ),
            },
            {
                "id": "enroll_vs_install_deb",
                "category": "navigation",
                "question": (
                    "When should you use `elastic-agent enroll` instead of "
                    "`elastic-agent install` on a DEB or RPM system?"
                ),
                "ground_truth": (
                    "Use enroll when you installed Elastic Agent from a DEB or RPM "
                    "package and plan to manage the service with systemd. Install "
                    "both installs the agent as a service and enrolls it in Fleet; "
                    "enroll only enrolls without installing as a service."
                ),
            },
            {
                "id": "root_recommendation",
                "category": "factual_retrieval",
                "question": (
                    "Why does the documentation recommend running the enroll or "
                    "install command as the root user?"
                ),
                "ground_truth": (
                    "Some integrations require root privileges to collect sensitive data."
                ),
            },
            {
                "id": "force_flag_risk",
                "category": "troubleshooting",
                "question": (
                    "What problem can occur if you use the `--force` flag to enroll "
                    "an agent that is already installed?"
                ),
                "ground_truth": (
                    "Using --force may result in unpredictable behavior with duplicate "
                    "Elastic Agents appearing in Fleet."
                ),
            },
            {
                "id": "replace_token_purpose",
                "category": "reasoning",
                "question": (
                    "Why would you need to supply `--replace-token` when enrolling "
                    "an agent with a specific `--id`?"
                ),
                "ground_truth": (
                    "If an agent with the same ID is already enrolled in Fleet, "
                    "enrollment will fail unless a valid replacement token is provided "
                    "via --replace-token."
                ),
            },
            {
                "id": "diagnostics_archive_contents",
                "category": "comprehension",
                "question": (
                    "List the main files included in the archive produced by "
                    "`elastic-agent diagnostics`."
                ),
                "ground_truth": (
                    "version.txt (version info), agent-info.yaml (agent local metadata), "
                    "pre-config.yaml (config before variable substitution), "
                    "variables.yaml (current variable contexts from providers), "
                    "otel.yaml (OTel collector config), "
                    "components/ directory (per-component diagnostics output)"
                ),
            },
        ],
    },
    {
        "id": "cross_cluster_search",
        "title": "Cross-Cluster Search",
        "md_url": (
            "https://www.elastic.co/docs/explore-analyze/cross-cluster-search.md"
        ),
        "html_url": (
            "https://www.elastic.co/docs/explore-analyze/cross-cluster-search"
        ),
        "tasks": [
            {
                "id": "ccs_index_syntax",
                "category": "code_extraction",
                "question": (
                    "What is the syntax to target an index on a remote cluster "
                    "in a cross-cluster search request?"
                ),
                "ground_truth": "<remote_cluster_name>:<target>",
            },
            {
                "id": "ccs_coordinating_prereq",
                "category": "factual_retrieval",
                "question": (
                    "What node role must the local coordinating node have to "
                    "perform cross-cluster search?"
                ),
                "ground_truth": "The remote_cluster_client node role.",
            },
            {
                "id": "ccs_sniff_vs_proxy",
                "category": "navigation",
                "question": (
                    "How do sniff mode and proxy mode differ in the connectivity "
                    "requirements placed on the local coordinating node?"
                ),
                "ground_truth": (
                    "Sniff mode: the local node must connect to seed and gateway nodes "
                    "on the remote cluster. "
                    "Proxy mode: the local node only connects to the configured "
                    "proxy_address; the proxy routes onward to gateway and coordinating nodes."
                ),
            },
            {
                "id": "ccs_skip_unavailable_failure",
                "category": "troubleshooting",
                "question": (
                    "What is the difference in outcome when a remote cluster is "
                    "unreachable during a cross-cluster search depending on the "
                    "`skip_unavailable` setting?"
                ),
                "ground_truth": (
                    "skip_unavailable=true: the cluster is skipped, the search succeeds "
                    "with partial results (HTTP 200). "
                    "skip_unavailable=false: if the cluster is unavailable, disconnects, "
                    "or has failures on ALL shards, the entire search fails."
                ),
            },
            {
                "id": "ccs_async_roundtrips_partial",
                "category": "comprehension",
                "question": (
                    "When doing an async cross-cluster search with "
                    "`ccs_minimize_roundtrips=true`, what partial results are "
                    "visible while the search is still running on some clusters?"
                ),
                "ground_truth": (
                    "Partial hits and aggregation results from clusters that have "
                    "already completed, plus partial aggregation results (but not "
                    "partial top hits) from the local cluster even before it finishes."
                ),
            },
            {
                "id": "ccs_skip_default_change",
                "category": "factual_retrieval",
                "question": (
                    "What was the default value of `skip_unavailable` before "
                    "Elasticsearch 8.15, and what did it change to in 8.15?"
                ),
                "ground_truth": (
                    "Before 8.15: false (remote clusters required by default). "
                    "From 8.15 onward: true (remote clusters optional by default)."
                ),
            },
            {
                "id": "ccs_roundtrip_tradeoff",
                "category": "reasoning",
                "question": (
                    "For an async cross-cluster search, what is the tradeoff between "
                    "setting `ccs_minimize_roundtrips=true` versus `false` in terms "
                    "of what partial results you see while the search is running?"
                ),
                "ground_truth": (
                    "With true: partial top hits and aggregations are visible per "
                    "completed cluster. "
                    "With false: no top hits until the search completes, but partial "
                    "aggregation results from individual shards (across any cluster) "
                    "appear as each shard finishes."
                ),
            },
        ],
    },
    {
        "id": "defend_advanced",
        "title": "Elastic Defend Advanced Settings",
        "md_url": (
            "https://www.elastic.co/docs/reference/security/defend-advanced-settings.md"
        ),
        "html_url": (
            "https://www.elastic.co/docs/reference/security/defend-advanced-settings"
        ),
        "tasks": [
            {
                "id": "artifact_interval_default",
                "category": "factual_retrieval",
                "question": (
                    "What is the default interval, in seconds, between protection "
                    "artifact update attempts?"
                ),
                "ground_truth": "3600 seconds (one hour).",
            },
            {
                "id": "channel_values",
                "category": "code_extraction",
                "question": (
                    "What are the three valid values for "
                    "`advanced.artifacts.global.channel` and what does each mean?"
                ),
                "ground_truth": (
                    "default: staged rollout (standard release cadence). "
                    "rapid: candidate artifacts delivered as soon as available. "
                    "stable: updates only after staged rollout has fully completed."
                ),
            },
            {
                "id": "airgap_settings",
                "category": "navigation",
                "question": (
                    "Which setting must be changed when configuring an air-gapped "
                    "environment to receive protection artifact updates from an "
                    "internal server?"
                ),
                "ground_truth": (
                    "advanced.artifacts.global.base_url must be changed to point to "
                    "the internal server. advanced.artifacts.global.manifest_relative_url "
                    "typically does not need to be modified."
                ),
            },
            {
                "id": "aggregate_process_behavior",
                "category": "comprehension",
                "question": (
                    "What does enabling `advanced.events.aggregate_process` do, and "
                    "from which version is it on by default?"
                ),
                "ground_truth": (
                    "It merges rapid process create/fork/exec/end events into a single "
                    "event document to reduce data volume. It is enabled by default "
                    "from version 8.18 onward (available since 8.16)."
                ),
            },
            {
                "id": "event_filter_default",
                "category": "reasoning",
                "question": (
                    "What happens when you disable `advanced.events.event_filter.default`, "
                    "and why does Elastic enable it by default?"
                ),
                "ground_truth": (
                    "Disabling it causes all events — including noisy system activity of "
                    "limited security value — to be collected and streamed to Elasticsearch. "
                    "It is enabled by default because Elastic maintains dynamic rules that "
                    "suppress known-noisy activity to reduce data volume."
                ),
            },
            {
                "id": "cloud_services_override",
                "category": "factual_retrieval",
                "question": (
                    "What keyword do you use in `advanced.cloud_services.enabled` to "
                    "disable all cloud services at once?"
                ),
                "ground_truth": "none",
            },
            {
                "id": "hash_exception_override",
                "category": "troubleshooting",
                "question": (
                    "If you set MD5, SHA-1, or SHA-256 hashing to `false` but you "
                    "have alert exceptions or trusted apps configured, will hashing "
                    "actually be disabled?"
                ),
                "ground_truth": (
                    "No. Hashes will still be collected if alert exceptions, trusted apps, "
                    "or blocklisting require them — the setting is ignored in those cases."
                ),
            },
        ],
    },
]
