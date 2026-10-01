// Frontend integration harness.
//
// Loads frontend/script.js inside a stubbed DOM, fires the real event
// handlers and verifies the chat flow: message sent to /chat, JSON
// handled, customer message + assistant answer displayed, optional
// response fields tolerated, API errors handled gracefully, upload
// results displayed and hostile backend text never rendered as HTML.
//
// It is executed by tests/test_frontend_runtime.py (which is skipped
// when Node.js 20+ is not available):
//
//     node tests/frontend_harness.js frontend/script.js

const fs = require("fs");
const vm = require("vm");

const scriptPath = process.argv[2];

if (!scriptPath) {
    console.error("usage: node frontend_harness.js <script.js>");
    process.exit(2);
}

const source = fs.readFileSync(scriptPath, "utf8");

const shown = [];
const panelHtml = [];
const requests = [];

let domReady = null;
let alertCount = 0;

function makeElement(tag) {

    const element = {
        tagName: tag,
        children: [],
        style: {},
        id: "",
        className: "",
        value: "",
        textContent: "",
        innerHTML: "",
        disabled: false,
        files: [],
        scrollHeight: 0,
        scrollTop: 0,
        appendChild(child) {
            element.children.push(child);
            return child;
        },
        remove() {
            element.removed = true;
        },
        addEventListener(name, handler) {
            element._handlers = element._handlers || {};
            element._handlers[name] = handler;
        },
        prepend() {},
        insertBefore() {},
        focus() {}
    };

    return element;
}

const chatBox = makeElement("div");
chatBox.id = "chatBox";

chatBox.appendChild = function (wrapper) {

    const bubble = (wrapper.children || []).find(
        (child) => child.className === "message-bubble"
    );

    const entry = { text: bubble ? bubble.textContent : "", removed: false };

    shown.push(entry);

    // The loading bubble is removed from the DOM once the response
    // arrives, so the harness models removal as well.
    wrapper.remove = function () {
        entry.removed = true;
    };

    return wrapper;
};

function visibleMessages() {

    return shown
        .filter((entry) => !entry.removed)
        .map((entry) => entry.text);
}

const messageInput = makeElement("input");
messageInput.id = "messageInput";

const sendButton = makeElement("button");
sendButton.id = "sendButton";

const fileInput = makeElement("input");
fileInput.id = "fileInput";

const uploadButton = makeElement("button");
uploadButton.id = "uploadButton";

const customerMessage = makeElement("textarea");
customerMessage.id = "customerMessage";

const resultPanel = makeElement("div");
resultPanel.id = "resultPanel";

Object.defineProperty(resultPanel, "innerHTML", {
    get() {
        return panelHtml[panelHtml.length - 1] || "";
    },
    set(value) {
        panelHtml.push(value);
    }
});

const byId = {
    chatBox,
    messageInput,
    sendButton,
    fileInput,
    uploadButton,
    customerMessage,
    resultPanel
};

const body = makeElement("body");

const documentStub = {
    body,
    addEventListener(name, handler) {
        if (name === "DOMContentLoaded") {
            domReady = handler;
        }
    },
    getElementById(id) {
        return byId[id] || null;
    },
    querySelector() {
        return null;
    },
    createElement(tag) {
        return makeElement(tag);
    }
};

messageInput.parentElement = { parentElement: body };

const storage = {};

const localStorageStub = {
    getItem(key) {
        return Object.prototype.hasOwnProperty.call(storage, key)
            ? storage[key]
            : null;
    },
    setItem(key, value) {
        storage[key] = String(value);
    }
};

let chatResponse = {};
let uploadResponse = {};

// failure: null | { mode: "status", status: number }
//          | { mode: "network" } | { mode: "malformed" }
let failure = null;

async function fetchStub(url, options) {

    requests.push({ url, options });

    if (failure) {

        const active = failure;

        failure = null;

        if (active.mode === "network") {
            throw new TypeError("fetch failed");
        }

        if (active.mode === "malformed") {
            return {
                ok: true,
                status: 200,
                json: async () => {
                    throw new SyntaxError("Unexpected token < in JSON");
                }
            };
        }

        return { ok: false, status: active.status };
    }

    if (url.endsWith("/chat")) {
        return { ok: true, status: 200, json: async () => chatResponse };
    }

    if (url.endsWith("/upload")) {
        return { ok: true, status: 200, json: async () => uploadResponse };
    }

    return { ok: true, status: 200, json: async () => ({ status: "online" }) };
}

const context = vm.createContext({
    document: documentStub,
    localStorage: localStorageStub,
    fetch: fetchStub,
    console,
    alert() {
        alertCount += 1;
    },
    setTimeout,
    clearTimeout,
    FormData,
    File,
    Blob,
    Date,
    JSON,
    Array,
    Boolean,
    String,
    Number,
    Object,
    Promise,
    Error,
    TypeError,
    SyntaxError
});

vm.runInContext(source, context, { filename: scriptPath });

function check(name, condition, detail) {

    if (condition) {
        console.log(`[PASS] ${name}`);
    } else {
        console.log(`[FAIL] ${name}${detail ? ` -> ${detail}` : ""}`);
        process.exitCode = 1;
    }
}

async function main() {

    check("DOMContentLoaded handler registered", typeof domReady === "function");

    domReady();

    await new Promise((resolve) => setTimeout(resolve, 50));

    check(
        "sendMessage/uploadFile are wired up",
        typeof context.sendMessage === "function" &&
            typeof context.uploadFile === "function"
    );

    // --------------------------------------------------------
    // 1. CHAT - normal response
    // --------------------------------------------------------

    chatResponse = {
        message: "My order ORD12345 has not been delivered",
        ticket_information: { order_id: "ORD12345", issue: "Order not delivered" },
        priority: "MEDIUM",
        severity: "Medium",
        ticket_ready: false,
        missing_information: ["order_id"],
        knowledge_base_answer: "Standard delivery normally takes 3 to 7 business days.",
        knowledge_base_sources: [{ filename: "delivery_policy.txt" }],
        rag_used: true,
        escalation: { escalated: false },
        after_hours: { after_hours: false }
    };

    messageInput.value = "My order ORD12345 has not been delivered";

    await context.sendMessage();

    const chatRequest = requests.find((request) => request.url.endsWith("/chat"));

    check("POST /chat was called", Boolean(chatRequest));

    check(
        "chat payload contains message, customer_id and user_role",
        Boolean(chatRequest) &&
            JSON.parse(chatRequest.options.body).message ===
                "My order ORD12345 has not been delivered" &&
            Boolean(JSON.parse(chatRequest.options.body).customer_id) &&
            JSON.parse(chatRequest.options.body).user_role === "PUBLIC"
    );

    check(
        "customer message displayed",
        visibleMessages()[0] === "My order ORD12345 has not been delivered",
        visibleMessages()[0]
    );

    const answer = visibleMessages()[1] || "";

    check("order ID displayed", answer.includes("Order ID: ORD12345"), answer);
    check("priority displayed", answer.includes("Priority: MEDIUM"), answer);
    check("severity displayed", answer.includes("Severity: Medium"), answer);
    check("RAG answer displayed", answer.includes("3 to 7 business days"), answer);
    check(
        "knowledge base source displayed",
        answer.includes("Source: delivery_policy.txt"),
        answer
    );
    check(
        "missing information displayed",
        answer.includes("Missing information: order_id"),
        answer
    );
    check("send button re-enabled", sendButton.disabled === false);
    check("message input cleared", messageInput.value === "");

    // --------------------------------------------------------
    // 2. CHAT - missing optional fields must not crash
    // --------------------------------------------------------

    chatResponse = { message: "hello" };

    messageInput.value = "hello";

    const before = visibleMessages().length;

    await context.sendMessage();

    check(
        "response without optional fields still displayed",
        visibleMessages().length === before + 2 &&
            visibleMessages().at(-1).includes(
                "I received your request successfully."
            ),
        visibleMessages().at(-1)
    );

    // --------------------------------------------------------
    // 3. CHAT - API errors handled gracefully
    // --------------------------------------------------------

    // 3a. Validation error returned by the backend (HTTP 422)

    failure = { mode: "status", status: 422 };

    messageInput.value = "trigger validation error";

    await context.sendMessage();

    check(
        "validation error (422) shown as a clean message",
        visibleMessages().at(-1).includes("could not process that message"),
        visibleMessages().at(-1)
    );

    // 3b. Unexpected backend failure (HTTP 500)

    failure = { mode: "status", status: 500 };

    messageInput.value = "trigger server error";

    await context.sendMessage();

    check(
        "server error (500) shown with its status",
        visibleMessages().at(-1).includes("status 500") &&
            !visibleMessages().at(-1).includes("{"),
        visibleMessages().at(-1)
    );

    // 3c. Backend unreachable (fetch rejects with a TypeError)

    failure = { mode: "network" };

    messageInput.value = "trigger network error";

    await context.sendMessage();

    check(
        "unreachable backend shown as a connection error",
        visibleMessages().at(-1).includes("Sorry, I could not connect"),
        visibleMessages().at(-1)
    );

    // 3d. Malformed (non-JSON) response body

    failure = { mode: "malformed" };

    messageInput.value = "trigger malformed response";

    await context.sendMessage();

    check(
        "malformed response handled gracefully",
        visibleMessages().at(-1).includes("unexpected response"),
        visibleMessages().at(-1)
    );

    // 3e. Empty / whitespace-only message is never sent

    const requestsBeforeEmpty = requests.length;

    const messagesBeforeEmpty = visibleMessages().length;

    messageInput.value = "   ";

    await context.sendMessage();

    check(
        "empty message is not sent to the backend",
        requests.length === requestsBeforeEmpty &&
            visibleMessages().length === messagesBeforeEmpty,
        `requests ${requestsBeforeEmpty} -> ${requests.length}`
    );

    check(
        "send button re-enabled after the error cases",
        sendButton.disabled === false
    );

    // --------------------------------------------------------
    // 4. UPLOAD - success
    // --------------------------------------------------------

    uploadResponse = {
        success: true,
        filename: "invoice.pdf",
        message: "File processed successfully.",
        extracted_text: "INVOICE\nOrder ID: ORD12345",
        extracted_information: {
            order_ids: ["ORD12345"],
            dates: ["2026-09-20"],
            amounts: ["Rs. 29,999"],
            product_names: ["Samsung Galaxy Phone"],
            error_codes: ["ERR-500"],
            comparison: {
                status: "MATCH",
                conflict: false,
                conflicts: [],
                message_order_ids: ["ORD12345"],
                file_order_ids: ["ORD12345"]
            }
        },
        processed_file: "data/uploads/processed/invoice.pdf"
    };

    fileInput.files = [
        new File(["data"], "invoice.pdf", { type: "application/pdf" })
    ];

    customerMessage.value = "My order ORD12345 is not working.";

    await context.uploadFile();

    const uploadRequest = requests.find(
        (request) => request.url.endsWith("/upload")
    );

    check("POST /upload was called", Boolean(uploadRequest));

    const uploadMessage = visibleMessages().at(-1) || "";

    check(
        "upload result displayed",
        uploadMessage.includes("File processed successfully.") &&
            uploadMessage.includes("ORD12345") &&
            uploadMessage.includes("ERR-500") &&
            uploadMessage.includes("MATCH"),
        uploadMessage
    );

    check(
        "analysis panel rendered with escaped values",
        panelHtml[panelHtml.length - 1].includes("invoice.pdf") &&
            panelHtml[panelHtml.length - 1].includes("ERR-500"),
        panelHtml.length
    );

    check("no alert shown for a valid upload", alertCount === 0);

    // --------------------------------------------------------
    // 5. UPLOAD - backend failure path
    // --------------------------------------------------------

    uploadResponse = {
        success: false,
        stage: "file_validation",
        filename: "bad.exe",
        message: "Unsupported file type.",
        issues: ["Unsupported file type: .exe"]
    };

    await context.uploadFile();

    const errorMessage = visibleMessages().at(-1) || "";

    check(
        "upload failure displayed",
        errorMessage.includes("Unsupported file type.") &&
            errorMessage.includes("file_validation"),
        errorMessage
    );

    check(
        "analysis error panel rendered",
        panelHtml[panelHtml.length - 1].includes("Processing failed"),
        panelHtml.length
    );

    // --------------------------------------------------------
    // 6. XSS safety - hostile backend text stays text
    // --------------------------------------------------------

    uploadResponse = {
        success: true,
        filename: '<img src=x onerror="alert(1)">.pdf',
        message: '<script>alert("xss")</script>',
        extracted_text: "<script>alert(1)</script>",
        extracted_information: {
            order_ids: ["<script>alert(1)</script>"],
            dates: [],
            amounts: [],
            product_names: [],
            error_codes: [],
            comparison: {
                status: "MATCH",
                conflict: false,
                conflicts: [],
                message_order_ids: [],
                file_order_ids: []
            }
        },
        processed_file: "data/uploads/processed/x.pdf"
    };

    await context.uploadFile();

    const renderedPanel = panelHtml[panelHtml.length - 1];

    check(
        "analysis panel escapes HTML from the backend",
        !renderedPanel.includes("<img src=x") &&
            !renderedPanel.includes("<script>alert"),
        renderedPanel.slice(0, 120)
    );

    check(
        "chat bubble keeps hostile text as plain text",
        visibleMessages().at(-1).includes("<script>alert(1)</script>"),
        visibleMessages().at(-1).slice(0, 200)
    );

    console.log(
        process.exitCode === 1
            ? "FRONTEND HARNESS: FAILURES DETECTED"
            : "FRONTEND HARNESS: ALL CHECKS PASSED"
    );
}

main().catch((error) => {
    console.error("[FAIL] harness crashed:", error);
    process.exitCode = 1;
});
