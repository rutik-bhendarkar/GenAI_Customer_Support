// ============================================================
// GENAI CUSTOMER SUPPORT - FRONTEND
// ============================================================

// ============================================================
// BACKEND URL
// ============================================================

// The backend URL can be overridden without editing this file by
// defining window.API_BASE_URL before script.js is loaded, for
// example in index.html:
//
//     <script>window.API_BASE_URL = "http://192.168.1.10:8000";</script>
//
// The default keeps the local FastAPI development server working.

const API_BASE_URL = (
    typeof window !== "undefined" &&
    window.API_BASE_URL
)
    ? window.API_BASE_URL
    : "http://127.0.0.1:8000";


// ============================================================
// GLOBAL VARIABLES
// ============================================================

let messageInput = null;
let sendButton = null;

let chatContainer = null;

let fileInput = null;
let uploadButton = null;
let customerMessageInput = null;

let resultPanel = null;


// ============================================================
// CUSTOMER SESSION
// ============================================================

let customerId = localStorage.getItem(
    "genai_customer_id"
);

if (!customerId) {

    customerId =
        "customer_" +
        Date.now();

    localStorage.setItem(
        "genai_customer_id",
        customerId
    );
}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        console.log("====================================");
        console.log("GenAI Customer Support Frontend");
        console.log("API:", API_BASE_URL);
        console.log("====================================");


        // ----------------------------------------------------
        // FIND CHAT INPUT
        // ----------------------------------------------------

        messageInput =
            document.getElementById("messageInput");


        // ----------------------------------------------------
        // FIND SEND BUTTON
        // ----------------------------------------------------

        sendButton =
            document.getElementById("sendButton") ||
            document.getElementById("sendBtn");


        // ----------------------------------------------------
        // FIND CHAT CONTAINER
        // ----------------------------------------------------

        chatContainer =
            document.getElementById("chatBox") ||
            document.getElementById("chatMessages") ||
            document.getElementById("chat-messages") ||
            document.querySelector(".chat-box") ||
            document.querySelector(".chat-messages");


        // ----------------------------------------------------
        // CREATE CHAT CONTAINER IF MISSING
        // ----------------------------------------------------

        if (!chatContainer) {

            console.warn(
                "Chat container was not found. Creating one."
            );


            chatContainer =
                document.createElement("div");


            chatContainer.id =
                "chatBox";


            chatContainer.className =
                "chat-box";


            chatContainer.style.height =
                "420px";


            chatContainer.style.overflowY =
                "auto";


            chatContainer.style.padding =
                "20px";


            chatContainer.style.background =
                "white";


            chatContainer.style.borderRadius =
                "12px";


            chatContainer.style.border =
                "1px solid #e2e8f0";


            // Try to place it before the input area

            if (
                messageInput &&
                messageInput.parentElement
            ) {

                messageInput.parentElement.parentElement.insertBefore(
                    chatContainer,
                    messageInput.parentElement
                );

            } else {

                document.body.prepend(
                    chatContainer
                );
            }
        }


        // ----------------------------------------------------
        // FILE INPUT
        // ----------------------------------------------------

        fileInput =
            document.getElementById("fileInput");


        // ----------------------------------------------------
        // UPLOAD BUTTON
        // ----------------------------------------------------

        uploadButton =
            document.getElementById("uploadButton") ||
            document.getElementById("uploadBtn");


        // ----------------------------------------------------
        // CUSTOMER MESSAGE FOR UPLOAD
        // ----------------------------------------------------

        customerMessageInput =
            document.getElementById("customerMessage") ||
            document.getElementById("customer_message");


        // ----------------------------------------------------
        // AI ANALYSIS RESULT PANEL
        // ----------------------------------------------------

        resultPanel =
            document.getElementById("resultPanel") ||
            document.querySelector(".result-panel");


        // ----------------------------------------------------
        // LOG ELEMENTS
        // ----------------------------------------------------

        console.log(
            "Message input:",
            messageInput
        );

        console.log(
            "Send button:",
            sendButton
        );

        console.log(
            "Chat container:",
            chatContainer
        );

        console.log(
            "File input:",
            fileInput
        );

        console.log(
            "Upload button:",
            uploadButton
        );


        // ----------------------------------------------------
        // SEND BUTTON
        // ----------------------------------------------------

        if (sendButton) {

            sendButton.addEventListener(
                "click",
                function (event) {

                    event.preventDefault();

                    sendMessage();
                }
            );
        }


        // ----------------------------------------------------
        // ENTER KEY
        // ----------------------------------------------------

        if (messageInput) {

            messageInput.addEventListener(
                "keydown",
                function (event) {

                    if (
                        event.key === "Enter" &&
                        !event.shiftKey
                    ) {

                        event.preventDefault();

                        sendMessage();
                    }
                }
            );
        }


        // ----------------------------------------------------
        // UPLOAD BUTTON
        // ----------------------------------------------------

        if (uploadButton) {

            uploadButton.addEventListener(
                "click",
                function (event) {

                    event.preventDefault();

                    uploadFile();
                }
            );
        }


        // ----------------------------------------------------
        // FILE SELECTION
        // ----------------------------------------------------

        if (fileInput) {

            fileInput.addEventListener(
                "change",
                function () {

                    if (
                        fileInput.files &&
                        fileInput.files.length > 0
                    ) {

                        console.log(
                            "Selected file:",
                            fileInput.files[0].name
                        );
                    }
                }
            );
        }


        // ----------------------------------------------------
        // BACKEND CHECK
        // ----------------------------------------------------

        checkBackend();
    }
);


// ============================================================
// BACKEND HEALTH CHECK
// ============================================================

async function checkBackend() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/`
            );


        if (response.ok) {

            console.log(
                "Backend connected successfully."
            );

        } else {

            console.warn(
                "Backend returned status:",
                response.status
            );
        }

    } catch (error) {

        console.error(
            "Backend connection failed:",
            error
        );
    }
}


// ============================================================
// USER FACING ERROR MESSAGES
// ============================================================

const NETWORK_ERROR_MESSAGE =
    "Sorry, I could not connect to the support server. " +
    "Please make sure the FastAPI backend is running.";


function getUserFacingErrorMessage(error) {

    // fetch() rejects with a TypeError when the backend cannot be
    // reached, so that case gets the connection hint. Any other
    // error already carries a customer-friendly message.

    if (error instanceof TypeError) {

        return NETWORK_ERROR_MESSAGE;
    }


    if (
        error &&
        typeof error.message === "string" &&
        error.message.trim()
    ) {

        return error.message;
    }


    return NETWORK_ERROR_MESSAGE;
}


// ============================================================
// ADD MESSAGE
// ============================================================

function addMessage(
    sender,
    text
) {

    if (!chatContainer) {

        console.error(
            "Chat container is not available."
        );

        return null;
    }


    const wrapper =
        document.createElement("div");


    if (sender === "user") {

        wrapper.className =
            "message user-message";

    } else {

        wrapper.className =
            "message assistant-message";
    }


    // --------------------------------------------------------
    // LABEL
    // --------------------------------------------------------

    const label =
        document.createElement("div");


    label.className =
        "message-label";


    label.textContent =
        sender === "user"
            ? "You"
            : "AI Assistant";


    // --------------------------------------------------------
    // BUBBLE
    // --------------------------------------------------------

    const bubble =
        document.createElement("div");


    bubble.className =
        "message-bubble";


    // IMPORTANT:
    // textContent is used instead of innerHTML
    // so backend/user content is displayed safely.

    bubble.textContent =
        text;


    // --------------------------------------------------------
    // BUILD MESSAGE
    // --------------------------------------------------------

    wrapper.appendChild(
        label
    );

    wrapper.appendChild(
        bubble
    );


    chatContainer.appendChild(
        wrapper
    );


    // --------------------------------------------------------
    // SCROLL TO BOTTOM
    // --------------------------------------------------------

    chatContainer.scrollTop =
        chatContainer.scrollHeight;


    return wrapper;
}


// ============================================================
// ADD LOADING MESSAGE
// ============================================================

function addLoadingMessage() {

    return addMessage(
        "assistant",
        "AI is processing your request..."
    );
}


// ============================================================
// HTML ESCAPING
// ============================================================

function escapeHtml(text) {

    if (text === null || text === undefined) {
        return "";
    }

    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ============================================================
// AI ANALYSIS PANEL HELPERS
// ============================================================

function getResultPanel() {

    if (!resultPanel) {

        resultPanel =
            document.getElementById("resultPanel") ||
            document.querySelector(".result-panel");
    }


    if (!resultPanel) {

        console.warn(
            "AI Analysis result panel was not found."
        );
    }


    return resultPanel;
}


function formatList(values) {

    if (
        !Array.isArray(values) ||
        values.length === 0
    ) {

        return "None detected";
    }


    return values.join(", ");
}


// ============================================================
// RENDER AI ANALYSIS - SUCCESS
// ============================================================

function renderAnalysisPanel(data) {

    const panel = getResultPanel();


    if (!panel) {

        return;
    }


    const information =
        data.extracted_information || {};


    const comparison =
        information.comparison || {};


    let html = "";


    // --------------------------------------------------------
    // SUMMARY
    // --------------------------------------------------------

    html += '<div class="result-block">';

    html += '<h3 class="result-title">✅ File processed successfully</h3>';

    html +=
        '<p class="result-row"><span>File:</span> ' +
        `<strong>${escapeHtml(data.filename || "unknown")}</strong></p>`;


    if (data.message) {

        html +=
            '<p class="result-row"><span>Message:</span> ' +
            `${escapeHtml(data.message)}</p>`;
    }


    html += "</div>";


    // --------------------------------------------------------
    // EXTRACTED INFORMATION
    // --------------------------------------------------------

    html += '<div class="result-block">';

    html += '<h4 class="result-subtitle">Extracted information</h4>';

    html +=
        '<p class="result-row"><span>Order IDs:</span> ' +
        `${escapeHtml(formatList(information.order_ids))}</p>`;

    html +=
        '<p class="result-row"><span>Dates:</span> ' +
        `${escapeHtml(formatList(information.dates))}</p>`;

    html +=
        '<p class="result-row"><span>Amounts:</span> ' +
        `${escapeHtml(formatList(information.amounts))}</p>`;

    html +=
        '<p class="result-row"><span>Products:</span> ' +
        `${escapeHtml(formatList(information.product_names))}</p>`;

    html +=
        '<p class="result-row"><span>Error codes:</span> ' +
        `${escapeHtml(formatList(information.error_codes))}</p>`;

    html += "</div>";


    // --------------------------------------------------------
    // COMPARISON - MESSAGE VS FILE
    // --------------------------------------------------------

    html += '<div class="result-block">';

    html += '<h4 class="result-subtitle">Message vs file comparison</h4>';

    html +=
        '<p class="result-row"><span>Status:</span> ' +
        `<span class="result-badge">${
            escapeHtml(comparison.status || "NO_COMPARISON")
        }</span></p>`;

    html +=
        '<p class="result-row"><span>Conflict:</span> ' +
        `${comparison.conflict === true ? "Yes" : "No"}</p>`;

    html +=
        '<p class="result-row"><span>Message order IDs:</span> ' +
        `${escapeHtml(formatList(comparison.message_order_ids))}</p>`;

    html +=
        '<p class="result-row"><span>File order IDs:</span> ' +
        `${escapeHtml(formatList(comparison.file_order_ids))}</p>`;


    if (
        Array.isArray(comparison.conflicts) &&
        comparison.conflicts.length > 0
    ) {

        html += '<ul class="result-conflicts">';


        comparison.conflicts.forEach(
            function (conflict) {

                html +=
                    `<li>${escapeHtml(
                        conflict.field || "field"
                    )}: ${escapeHtml(conflict.message || "")}</li>`;
            }
        );


        html += "</ul>";
    }


    html += "</div>";


    html += "</div>";


    // --------------------------------------------------------
    // EXTRACTED TEXT
    // --------------------------------------------------------

    if (data.extracted_text) {

        html += '<div class="result-block">';

        html += '<h4 class="result-subtitle">Extracted text</h4>';

        html +=
            `<pre class="result-text">${
                escapeHtml(data.extracted_text)
            }</pre>`;

        html += "</div>";
    }


    // --------------------------------------------------------
    // PROCESSED FILE
    // --------------------------------------------------------

    if (data.processed_file) {

        html +=
            '<p class="result-footer">Stored at: ' +
            `${escapeHtml(data.processed_file)}</p>`;
    }


    panel.innerHTML = html;
}


// ============================================================
// RENDER AI ANALYSIS - FAILURE
// ============================================================

function renderAnalysisError(data) {

    const panel = getResultPanel();


    if (!panel) {

        return;
    }


    const details = data || {};


    let html = "";


    html += '<div class="result-block result-block-error">';

    html += '<h3 class="result-title">❌ Processing failed</h3>';

    html +=
        '<p class="result-row"><span>File:</span> ' +
        `<strong>${escapeHtml(details.filename || "unknown")}</strong></p>`;


    if (details.stage) {

        html +=
            '<p class="result-row"><span>Stage:</span> ' +
            `${escapeHtml(details.stage)}</p>`;
    }


    html +=
        '<p class="result-row"><span>Reason:</span> ' +
        `${escapeHtml(
            details.message || "The file could not be processed."
        )}</p>`;


    if (details.error) {

        html +=
            '<p class="result-row"><span>Details:</span> ' +
            `${escapeHtml(details.error)}</p>`;
    }


    if (
        Array.isArray(details.issues) &&
        details.issues.length > 0
    ) {

        html +=
            '<p class="result-row"><span>Issues:</span> ' +
            `${escapeHtml(details.issues.join(", "))}</p>`;
    }


    if (
        Array.isArray(details.detected_patterns) &&
        details.detected_patterns.length > 0
    ) {

        html +=
            '<p class="result-row"><span>Detected patterns:</span> ' +
            `${escapeHtml(details.detected_patterns.join(", "))}</p>`;
    }


    html += "</div>";


    panel.innerHTML = html;
}


// ============================================================
// SEND CHAT MESSAGE
// ============================================================

async function sendMessage() {

    console.log(
        "Send button clicked."
    );


    if (!messageInput) {

        console.error(
            "messageInput not found."
        );

        return;
    }


    const message =
        messageInput.value.trim();


    if (!message) {

        return;
    }


    // --------------------------------------------------------
    // SHOW USER MESSAGE
    // --------------------------------------------------------

    addMessage(
        "user",
        message
    );


    // --------------------------------------------------------
    // CLEAR INPUT
    // --------------------------------------------------------

    messageInput.value = "";


    // --------------------------------------------------------
    // DISABLE BUTTON
    // --------------------------------------------------------

    if (sendButton) {

        sendButton.disabled =
            true;

        sendButton.textContent =
            "Sending...";
    }


    // --------------------------------------------------------
    // LOADING MESSAGE
    // --------------------------------------------------------

    const loadingMessage =
        addLoadingMessage();


    try {

        console.log(
            "Sending message to backend:",
            message
        );


        // ----------------------------------------------------
        // REQUEST
        // ----------------------------------------------------

        const response =
            await fetch(
                `${API_BASE_URL}/chat`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            message:
                                message,

                            customer_id:
                                customerId,

                            user_role:
                                "PUBLIC"
                        })
                }
            );


        console.log(
            "Chat response status:",
            response.status
        );


        if (!response.ok) {

            const status = response.status;


            // Validation errors (empty or malformed message)

            if (status === 400 || status === 422) {

                throw new Error(
                    "I could not process that message. " +
                    "Please check it and try again."
                );
            }


            throw new Error(
                "The support server reported an error " +
                `(status ${status}). Please try again.`
            );
        }


        let data = null;


        try {

            data = await response.json();

        } catch (parseError) {

            // Malformed / non-JSON response from the backend.

            throw new Error(
                "The support server returned an unexpected " +
                "response. Please try again."
            );
        }


        console.log(
            "Chat backend response:",
            data
        );


        // ----------------------------------------------------
        // REMOVE LOADING MESSAGE
        // ----------------------------------------------------

        if (loadingMessage) {

            loadingMessage.remove();
        }


        // ----------------------------------------------------
        // BUILD REAL RESPONSE
        // ----------------------------------------------------

        let answer = "";


        // Knowledge base answer

        if (
            data.knowledge_base_answer &&
            data.knowledge_base_answer.trim()
        ) {

            answer =
                data.knowledge_base_answer;
        }


        // If no knowledge-base answer

        if (!answer) {

            answer =
                "I received your request successfully.";
        }


        // ----------------------------------------------------
        // ORDER INFORMATION
        // ----------------------------------------------------

        if (
            data.ticket_information &&
            data.ticket_information.order_id
        ) {

            answer +=
                `\n\nOrder ID: ${
                    data.ticket_information.order_id
                }`;
        }


        // ----------------------------------------------------
        // PRIORITY
        // ----------------------------------------------------

        if (data.priority) {

            answer +=
                `\nPriority: ${data.priority}`;
        }


        // ----------------------------------------------------
        // SEVERITY
        // ----------------------------------------------------

        if (data.severity) {

            answer +=
                `\nSeverity: ${data.severity}`;
        }


        // ----------------------------------------------------
        // TICKET READINESS / MISSING INFORMATION
        // ----------------------------------------------------

        if (
            data.ticket_ready === false &&
            Array.isArray(data.missing_information) &&
            data.missing_information.length > 0
        ) {

            answer +=
                `\nMissing information: ${
                    data.missing_information.join(", ")
                }`;
        }


        // ----------------------------------------------------
        // KNOWLEDGE BASE SOURCES
        // ----------------------------------------------------

        if (
            Array.isArray(data.knowledge_base_sources) &&
            data.knowledge_base_sources.length > 0
        ) {

            const sourceNames =
                data.knowledge_base_sources
                    .map(
                        function (source) {

                            return (
                                source &&
                                source.filename
                            )
                                ? source.filename
                                : null;
                        }
                    )
                    .filter(
                        function (name) {

                            return Boolean(name);
                        }
                    );


            if (sourceNames.length > 0) {

                answer +=
                    `\nSource: ${
                        sourceNames.join(", ")
                    }`;
            }
        }


        // ----------------------------------------------------
        // ESCALATION
        // ----------------------------------------------------

        if (
            data.escalation &&
            data.escalation.escalated === true
        ) {

            answer +=
                "\n\n⚠ Your issue has been escalated for further support.";
        }


        // ----------------------------------------------------
        // AFTER HOURS
        // ----------------------------------------------------

        if (
            data.after_hours &&
            data.after_hours.after_hours === true
        ) {

            if (
                data.after_hours.queue
            ) {

                answer +=
                    `\n\nSupport queue: ${
                        data.after_hours.queue
                    }`;
            }
        }


        // ----------------------------------------------------
        // DISPLAY AI RESPONSE
        // ----------------------------------------------------

        addMessage(
            "assistant",
            answer
        );


    } catch (error) {

        console.error(
            "Chat error:",
            error
        );


        if (loadingMessage) {

            loadingMessage.remove();
        }


        addMessage(
            "assistant",
            getUserFacingErrorMessage(error)
        );


    } finally {

        if (sendButton) {

            sendButton.disabled =
                false;

            sendButton.textContent =
                "Send";
        }


        if (messageInput) {

            messageInput.focus();
        }
    }
}


// ============================================================
// FILE UPLOAD
// ============================================================

async function uploadFile() {

    console.log(
        "Upload button clicked."
    );


    if (!fileInput) {

        alert(
            "File input was not found."
        );

        return;
    }


    const file =
        fileInput.files[0];


    if (!file) {

        alert(
            "Please select a file first."
        );

        return;
    }


    // --------------------------------------------------------
    // CUSTOMER MESSAGE
    // --------------------------------------------------------

    let customerMessage = "";


    if (customerMessageInput) {

        customerMessage =
            customerMessageInput.value.trim();
    }


    // --------------------------------------------------------
    // FORM DATA
    // --------------------------------------------------------

    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    formData.append(
        "customer_message",
        customerMessage
    );


    // --------------------------------------------------------
    // DISABLE BUTTON
    // --------------------------------------------------------

    if (uploadButton) {

        uploadButton.disabled =
            true;

        uploadButton.textContent =
            "Processing...";
    }


    // --------------------------------------------------------
    // SHOW LOADING
    // --------------------------------------------------------

    const loadingMessage =
        addMessage(
            "assistant",
            `Processing file: ${file.name}...`
        );


    try {

        console.log(
            "Uploading:",
            file.name
        );


        // ----------------------------------------------------
        // SEND FILE
        // ----------------------------------------------------

        const response =
            await fetch(
                `${API_BASE_URL}/upload`,
                {
                    method: "POST",

                    body:
                        formData
                }
            );


        console.log(
            "Upload response status:",
            response.status
        );


        if (!response.ok) {

            if (
                response.status === 400 ||
                response.status === 422
            ) {

                throw new Error(
                    "That file could not be accepted. " +
                    "Please check the file type and size."
                );
            }


            throw new Error(
                "The support server reported an error " +
                `(status ${response.status}). Please try again.`
            );
        }


        let data = null;


        try {

            data = await response.json();

        } catch (parseError) {

            throw new Error(
                "The support server returned an unexpected " +
                "response. Please try again."
            );
        }


        console.log(
            "Upload backend response:",
            data
        );


        // Remove loading message

        if (loadingMessage) {

            loadingMessage.remove();
        }


        // ----------------------------------------------------
        // PROCESSING FAILED
        // ----------------------------------------------------

        if (!data.success) {

            let errorMessage =
                data.message ||
                "The file could not be processed.";


            if (data.stage) {

                errorMessage +=
                    `\nStage: ${data.stage}`;
            }


            addMessage(
                "assistant",
                `❌ ${errorMessage}`
            );


            // Show the failure details in the
            // AI Analysis panel as well.

            renderAnalysisError(data);


            return;
        }


        // ----------------------------------------------------
        // SUCCESS
        // ----------------------------------------------------

        let result =
            "✅ File processed successfully.";


        result +=
            `\nFile: ${data.filename}`;


        // ----------------------------------------------------
        // EXTRACTED INFORMATION
        // ----------------------------------------------------

        const information =
            data.extracted_information || {};


        if (
            information.order_ids &&
            information.order_ids.length > 0
        ) {

            result +=
                `\nOrder ID: ${
                    information.order_ids.join(", ")
                }`;
        }


        if (
            information.product_names &&
            information.product_names.length > 0
        ) {

            result +=
                `\nProduct: ${
                    information.product_names.join(", ")
                }`;
        }


        if (
            information.amounts &&
            information.amounts.length > 0
        ) {

            result +=
                `\nAmount: ${
                    information.amounts.join(", ")
                }`;
        }


        if (
            information.dates &&
            information.dates.length > 0
        ) {

            result +=
                `\nDate: ${
                    information.dates.join(", ")
                }`;
        }


        if (
            information.error_codes &&
            information.error_codes.length > 0
        ) {

            result +=
                `\nError Code: ${
                    information.error_codes.join(", ")
                }`;
        }


        // ----------------------------------------------------
        // COMPARISON
        // ----------------------------------------------------

        if (
            information.comparison
        ) {

            result +=
                `\n\nComparison: ${
                    information.comparison.status
                }`;


            if (
                information.comparison.conflict === true
            ) {

                result +=
                    "\n⚠ Conflict detected between the file and customer message.";
            }
        }


        // ----------------------------------------------------
        // OCR TEXT
        // ----------------------------------------------------

        if (data.extracted_text) {

            result +=
                "\n\nExtracted text:\n" +
                data.extracted_text;
        }


        // ----------------------------------------------------
        // SHOW RESULT
        // ----------------------------------------------------

        addMessage(
            "assistant",
            result
        );


        // ----------------------------------------------------
        // SHOW RESULT IN THE AI ANALYSIS PANEL
        // ----------------------------------------------------

        renderAnalysisPanel(data);


    } catch (error) {

        console.error(
            "Upload error:",
            error
        );


        if (loadingMessage) {

            loadingMessage.remove();
        }


        addMessage(
            "assistant",
            `❌ ${getUserFacingErrorMessage(error)}`
        );


        renderAnalysisError({
            filename:
                file ? file.name : "unknown",
            stage: "frontend_request",
            message: "The upload request could not be completed.",
            error: error.message
        });


    } finally {

        if (uploadButton) {

            uploadButton.disabled =
                false;

            uploadButton.textContent =
                "Upload & Process";
        }
    }
}