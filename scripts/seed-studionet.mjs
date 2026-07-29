import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

const CONTRACT = "0x2aB48F7021Bdda0435e5284D805235E8b16A8f18";
const env = readFileSync(resolve(process.cwd(), "../.env"), "utf8");
const privateKey = env
  .split(/\r?\n/)
  .find((line) => line.startsWith("GENLAYER_PRIVATE_KEY_0="))
  ?.slice("GENLAYER_PRIVATE_KEY_0=".length)
  .trim();

if (!privateKey) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const client = createClient({
  chain: studionet,
  account: createAccount(privateKey),
});

const retryRpc = async (operation, attempts = 30) => {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      const message = String(error?.details || error?.message || error);
      if (!message.includes("Server busy") || attempt === attempts) throw error;
      await new Promise((resolveDelay) => setTimeout(resolveDelay, attempt * 2_000));
    }
  }
};

const pilots = [
  {
    title: "ProofFund Protocol Launch",
    category: "Public goods",
    summary:
      "A live milestone escrow for public work, governed by evidence and appealable AI consensus.",
    description:
      "This StudioNet project tracks the public launch of ProofFund itself: a milestone funding protocol where capital remains in escrow until validators independently verify explicit acceptance criteria against public web evidence.",
    website: "https://docs.genlayer.com/",
    image: "https://images.unsplash.com/photo-1484417894907-623942c8ee29",
    goal: 25n,
    milestones: [
      {
        title: "StudioNet protocol core",
        criteria:
          "The deployed StudioNet contract exposes project creation, payable funding escrow, milestone evidence submission, consensus evaluation, bonded disputes, reputation, and claim methods in its public schema.",
        amount: 8n,
        due: "2026-08-31T00:00:00Z",
      },
      {
        title: "Validator-ready application",
        criteria:
          "The public application connects to this StudioNet contract, reads live project and reputation state, signs wallet actions, and exposes funding, evidence, evaluation, dispute, and claim workflows.",
        amount: 9n,
        due: "2026-10-01T00:00:00Z",
      },
      {
        title: "End-to-end adjudication proof",
        criteria:
          "A public evidence submission is evaluated by multiple validators, the resulting verdict and score persist on-chain, and the dispute path remains available with bonded counter-evidence.",
        amount: 8n,
        due: "2026-12-01T00:00:00Z",
      },
    ],
  },
  {
    title: "Open Source Security Atlas",
    category: "Infrastructure",
    summary:
      "Map reproducible security signals across critical open-source dependencies.",
    description:
      "An independent ProofFund pilot that publishes a searchable security atlas for widely used open-source packages. The work combines documented source selection, reproducible risk criteria, and public evidence so maintainers and downstream teams can inspect every finding.",
    website: "https://owasp.org/www-project-dependency-check/",
    image: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31",
    goal: 18n,
    milestone: "Publish the first verified dependency cohort",
    criteria:
      "A public HTTPS page lists at least twenty dependencies, explains the risk methodology, links each source, and provides machine-readable export instructions.",
  },
  {
    title: "Civic Data Commons",
    category: "Public goods",
    summary:
      "Turn fragmented civic datasets into a documented, reusable public catalog.",
    description:
      "An independent public-data pilot that organizes high-value civic datasets around provenance, licensing, refresh cadence, and practical reuse. Every release is designed to be inspected through public URLs and evaluated against explicit completeness criteria.",
    website: "https://data.gov/",
    image: "https://images.unsplash.com/photo-1451187580459-43490279c0fa",
    goal: 22n,
    milestone: "Release the catalog foundation",
    criteria:
      "A public catalog contains at least thirty dataset records with source URL, owner, license, update cadence, topic, and a documented process for proposing corrections.",
  },
  {
    title: "Climate Sensor Registry",
    category: "Climate",
    summary:
      "Create an auditable registry for community-operated environmental sensors.",
    description:
      "A community infrastructure pilot for documenting environmental sensors, calibration status, coverage, and public data endpoints. The registry prioritizes provenance and reproducibility so validator review can separate operational sensors from unsupported claims.",
    website: "https://wmo.int/",
    image: "https://images.unsplash.com/photo-1569163139394-de4e4f43e4e5",
    goal: 28n,
    milestone: "Verify the first sensor network",
    criteria:
      "A public registry documents at least fifteen sensors with location region, measurement type, calibration date, operator, live or archived data URL, and evidence of recent readings.",
  },
  {
    title: "Accessible Web Toolkit",
    category: "Open source",
    summary:
      "Ship practical accessibility checks that teams can run before deployment.",
    description:
      "An open-source pilot focused on repeatable accessibility verification for product teams. The toolkit translates established accessibility guidance into documented checks, example fixtures, and a public execution path suitable for independent review.",
    website: "https://www.w3.org/WAI/standards-guidelines/wcag/",
    image: "https://images.unsplash.com/photo-1559028012-481c04fa702d",
    goal: 16n,
    milestone: "Deliver the runnable audit toolkit",
    criteria:
      "A public repository includes installation instructions, runnable checks covering at least ten accessibility rules, passing and failing fixtures, license information, and generated sample output.",
  },
  {
    title: "Reproducibility Index",
    category: "Research",
    summary:
      "Score whether public research artifacts can be independently reproduced.",
    description:
      "A research infrastructure pilot that evaluates the availability and usability of code, data, environment definitions, and execution instructions. The index publishes its rubric and evidence so every score can be challenged or independently repeated.",
    website: "https://www.cos.io/products/osf",
    image: "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69",
    goal: 24n,
    milestone: "Publish the first reproducibility cohort",
    criteria:
      "A public report evaluates at least twelve research artifacts using a published rubric, links all inspected sources, explains exclusions, and includes a downloadable structured results file.",
  },
  {
    title: "Local Journalism Archive",
    category: "Public goods",
    summary:
      "Preserve and index public-interest local reporting with durable provenance.",
    description:
      "An archival pilot for organizing local public-interest reporting into a durable, searchable collection. It records original source, publication context, capture status, and topic metadata while respecting public access and provenance requirements.",
    website: "https://archive.org/",
    image: "https://images.unsplash.com/photo-1504711434969-e33886168f5c",
    goal: 20n,
    milestone: "Open the first indexed collection",
    criteria:
      "A public collection exposes at least fifty indexed records with original source, publication date, topic, archive status, searchable metadata, and a documented correction process.",
  },
  {
    title: "Open Credential Map",
    category: "Education",
    summary:
      "Make public learning credentials comparable through transparent mappings.",
    description:
      "An education pilot that maps public learning credentials to skills, issuing requirements, evidence standards, and source documentation. The project emphasizes traceable claims rather than rankings, enabling independent verification of every mapping.",
    website: "https://www.unesco.org/en/education",
    image: "https://images.unsplash.com/photo-1523050854058-8df90110c9f1",
    goal: 14n,
    milestone: "Release the initial credential map",
    criteria:
      "A public map includes at least twenty credentials with issuer, source URL, documented requirements, mapped skills, evidence standard, and an explanation of the mapping methodology.",
  },
  {
    title: "Humanitarian Logistics Monitor",
    category: "Infrastructure",
    summary:
      "Track public logistics signals for faster, evidence-based aid coordination.",
    description:
      "A humanitarian data pilot that organizes public logistics and access signals into a documented operational view. It focuses on source attribution, freshness, uncertainty, and clear limitations so decisions are grounded in inspectable evidence.",
    website: "https://data.humdata.org/",
    image: "https://images.unsplash.com/photo-1593113598332-cd288d649433",
    goal: 30n,
    milestone: "Publish the operational data view",
    criteria:
      "A public dashboard documents at least three logistics signal categories, identifies each source and refresh time, displays uncertainty or limitations, and provides a downloadable snapshot.",
  },
];

const atto = (gen) => gen * 10n ** 18n;
const deadline = Math.floor(new Date("2027-06-30T00:00:00Z").getTime() / 1000);
const trancheDeadlines = [
  Math.floor(new Date("2026-10-31T00:00:00Z").getTime() / 1000),
  Math.floor(new Date("2027-02-28T00:00:00Z").getTime() / 1000),
  deadline,
];
const milestoneDue = Math.floor(
  new Date("2027-03-31T00:00:00Z").getTime() / 1000,
);

const getLeader = (receipt) =>
  receipt?.consensus_data?.leader_receipt?.[0] ||
  receipt?.consensusData?.leaderReceipt?.[0];

const requireSuccess = (receipt, label) => {
  const leader = getLeader(receipt);
  if (leader?.execution_result === "SUCCESS" || leader?.executionResult === "SUCCESS") {
    return;
  }
  const detail =
    leader?.genvm_result?.error_description ||
    leader?.genvm_result?.stderr ||
    leader?.result?.payload?.readable ||
    "unknown execution error";
  throw new Error(`${label}: ${detail}`);
};

const send = async (functionName, args, label) => {
  const hash = await retryRpc(() =>
    client.writeContract({
      address: CONTRACT,
      functionName,
      args,
      value: 0n,
    }),
  );
  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
    interval: 3_000,
    retries: 100,
  });
  requireSuccess(receipt, label);
  return { hash, receipt };
};

const current = await retryRpc(() =>
  client.readContract({
    address: CONTRACT,
    functionName: "get_projects",
    args: [],
    jsonSafeReturn: true,
  }),
);
const existingTitles = new Set(current.map((project) => project.title));

for (const pilot of pilots) {
  if (existingTitles.has(pilot.title)) {
    console.log(`skip ${pilot.title}`);
    continue;
  }

  const firstGoal = pilot.goal / 3n;
  const secondGoal = pilot.goal / 3n;
  const thirdGoal = pilot.goal - firstGoal - secondGoal;
  const created = await send(
    "create_project",
    [
      pilot.title,
      pilot.category,
      pilot.summary,
      pilot.description,
      pilot.website,
      pilot.image,
      atto(pilot.goal),
      deadline,
      "Discovery and public specification",
      atto(firstGoal),
      trancheDeadlines[0],
    ],
    `create ${pilot.title}`,
  );
  const readable = getLeader(created.receipt)?.result?.payload?.readable;
  const projectId = JSON.parse(readable);
  console.log(`created ${projectId} ${pilot.title} ${created.hash}`);

  const stagedTranches = [
    ["Implementation and public preview", secondGoal, trancheDeadlines[1]],
    ["Verification, release, and maintenance", thirdGoal, trancheDeadlines[2]],
  ];
  for (const [title, goal, closesAt] of stagedTranches) {
    const tranche = await send(
      "add_funding_tranche",
      [projectId, title, atto(goal), closesAt],
      `tranche ${projectId}`,
    );
    console.log(`tranche ${projectId} ${tranche.hash}`);
  }

  const milestones = pilot.milestones || [
    {
      title: pilot.milestone,
      criteria: pilot.criteria,
      amount: pilot.goal,
      due: milestoneDue,
    },
  ];
  for (const item of milestones) {
    const dueAt =
      typeof item.due === "string"
        ? Math.floor(new Date(item.due).getTime() / 1000)
        : item.due;
    const milestone = await send(
      "add_milestone",
      [
        projectId,
        item.title,
        item.criteria,
        atto(item.amount),
        dueAt,
      ],
      `milestone ${pilot.title}`,
    );
    console.log(`milestone ${projectId} ${milestone.hash}`);
  }
}

const finalProjects = await retryRpc(() =>
  client.readContract({
    address: CONTRACT,
    functionName: "get_projects",
    args: [],
    jsonSafeReturn: true,
  }),
);
console.log(`total projects ${finalProjects.length}`);
