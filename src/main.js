/**
 * @fileoverview JSME (JavaScript Molecule Editor) integration with Gradio interface
 * Handles bidirectional synchronization between JSME applet and Gradio textbox
 * @author Manny Cortes ('manny@derifyai.com')
 * @version 0.1.0
 */

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

/** @type {Object|null} The JSME applet instance */
let jsmeApplet = null;

/** @type {string} Last known value of the textbox to prevent infinite loops */
let lastTextboxValue = "";

// ============================================================================
// CONSTANTS
// ============================================================================

/** @const {string} Default SMILES for initial molecule (ethanol) */
const DEFAULT_SMILES = "CCO";

/** @const {string} CSS selector for the Gradio SMILES input element */
const SMILES_INPUT_SELECTOR = "#smiles_input textarea, #smiles_input input";

/** @const {number} Maximum attempts to find textbox before giving up */
const MAX_TEXTBOX_FIND_ATTEMPTS = 20;

/** @const {number} Interval for retrying textbox discovery (ms) */
const TEXTBOX_FIND_INTERVAL = 500;

/** @const {number} Interval for periodic textbox monitoring (ms) */
const TEXTBOX_MONITOR_INTERVAL = 1000;

/** @const {number} Delay for paste event handling (ms) */
const PASTE_DELAY = 50;

/** @const {number} Delay for initialization retry (ms) */
const INIT_RETRY_DELAY = 1000;

/** @const {string[]} Events to trigger for Gradio change detection */
const GRADIO_CHANGE_EVENTS = ["input", "change", "keyup"];

// ============================================================================
// CORE INITIALIZATION
// ============================================================================

/**
 * Initializes the JSME applet after the library has been loaded
 * Sets up the molecular editor with default options and callbacks
 * @throws {Error} When JSME initialization fails
 */
function initializeJSME() {
  try {
    console.log("Initializing JSME...");

    // https://github.com/jsme-editor/jsme-editor.github.io
    // http://wiki.jmol.org/index.php/Jmol_JavaScript_Object/JME/Options
    jsmeApplet = new JSApplet.JSME("jsme_container", "100%", "450px", {
      options:
        "rButton,zoom,zoomgui,newLook,star,multipart,polarnitro,NOexportInChI,NOexportInChIkey,NOsearchInChIkey,NOexportSVG,NOpaste",
    });

    jsmeApplet.setCallBack("AfterStructureModified", handleJSMEStructureChange);

    // Set initial molecule and sync state
    jsmeApplet.readGenericMolecularInput(DEFAULT_SMILES);
    lastTextboxValue = DEFAULT_SMILES;

    setupTextboxMonitoring();

    console.log("JSME initialized successfully");
  } catch (error) {
    console.error("Error initializing JSME:", error);
    throw error;
  }
}

/**
 * Handles structure changes in the JSME applet
 * Converts the structure to SMILES and updates the Gradio textbox
 * @param {Event} event - The JSME structure modification event
 */
function handleJSMEStructureChange(event) {
  try {
    const smiles = jsmeApplet.smiles();
    updateGradioTextbox(smiles);
  } catch (error) {
    console.error("Error getting SMILES from JSME:", error);
  }
}

// ============================================================================
// GRADIO INTEGRATION
// ============================================================================

/**
 * Updates the Gradio textbox with a SMILES string
 * Triggers appropriate events to ensure Gradio detects the change
 * @param {string} smiles - The SMILES string to set in the textbox
 */
function updateGradioTextbox(smiles) {
  try {
    const textbox = document.querySelector(SMILES_INPUT_SELECTOR);

    if (!textbox || textbox.value === smiles) {
      return;
    }

    textbox.value = smiles;
    lastTextboxValue = smiles;

    // Trigger events to ensure Gradio detects the change
    GRADIO_CHANGE_EVENTS.forEach((eventType) => {
      const event = new Event(eventType, {
        bubbles: true,
        cancelable: true,
      });
      textbox.dispatchEvent(event);
    });
  } catch (error) {
    console.error("Error updating Gradio textbox:", error);
  }
}

// ============================================================================
// JSME UPDATE FUNCTIONS
// ============================================================================

/**
 * Updates the JSME applet with a SMILES string from the textbox
 * @param {string} smiles - The SMILES string to display in JSME
 */
function updateJSMEFromTextbox(smiles) {
  if (!jsmeApplet) {
    return;
  }

  try {
    if (smiles && smiles.trim() !== "") {
      jsmeApplet.readGenericMolecularInput(smiles.trim());
    } else {
      jsmeApplet.reset();
    }
    lastTextboxValue = smiles;
  } catch (error) {
    console.error("Error updating JSME from textbox:", error);
  }
}

// ============================================================================
// TEXTBOX MONITORING
// ============================================================================

/**
 * Sets up monitoring for changes in the Gradio textbox
 * Implements multiple strategies to ensure reliable change detection
 */
function setupTextboxMonitoring() {
  if (!findAndSetupTextbox()) {
    retryTextboxSetup();
  }

  setupPeriodicTextboxCheck();
}

/**
 * Finds the textbox element and sets up event listeners
 * @returns {boolean} True if textbox was found and set up successfully
 */
function findAndSetupTextbox() {
  const textbox = document.querySelector(SMILES_INPUT_SELECTOR);

  if (!textbox) {
    return false;
  }

  removeTextboxListeners(textbox);
  addTextboxListeners(textbox);

  // Perform initial sync if needed
  if (textbox.value && textbox.value !== lastTextboxValue) {
    updateJSMEFromTextbox(textbox.value);
  }

  return true;
}

/**
 * Removes event listeners from the textbox
 * @param {HTMLElement} textbox - The textbox element
 */
function removeTextboxListeners(textbox) {
  textbox.removeEventListener("input", handleTextboxChange);
  textbox.removeEventListener("change", handleTextboxChange);
  textbox.removeEventListener("paste", handleTextboxPaste);
  textbox.removeEventListener("keyup", handleTextboxChange);
}

/**
 * Adds event listeners to the textbox
 * @param {HTMLElement} textbox - The textbox element
 */
function addTextboxListeners(textbox) {
  textbox.addEventListener("input", handleTextboxChange);
  textbox.addEventListener("change", handleTextboxChange);
  textbox.addEventListener("paste", handleTextboxPaste);
  textbox.addEventListener("keyup", handleTextboxChange);
}

/**
 * Handles textbox change events
 * @param {Event} event - The change event
 */
function handleTextboxChange(event) {
  if (event.target.value !== lastTextboxValue) {
    updateJSMEFromTextbox(event.target.value);
  }
}

/**
 * Handles textbox paste events with a delay to ensure content is available
 * @param {Event} event - The paste event
 */
function handleTextboxPaste(event) {
  setTimeout(() => {
    updateJSMEFromTextbox(event.target.value);
  }, PASTE_DELAY);
}

/**
 * Retries textbox setup with exponential backoff
 */
function retryTextboxSetup() {
  let attempts = 0;

  const retryInterval = setInterval(() => {
    attempts++;

    if (findAndSetupTextbox() || attempts >= MAX_TEXTBOX_FIND_ATTEMPTS) {
      clearInterval(retryInterval);

      if (attempts >= MAX_TEXTBOX_FIND_ATTEMPTS) {
        console.error(
          `Could not find textbox after ${MAX_TEXTBOX_FIND_ATTEMPTS} attempts`
        );
      }
    }
  }, TEXTBOX_FIND_INTERVAL);
}

/**
 * Sets up periodic checking for textbox changes as a fallback mechanism
 */
function setupPeriodicTextboxCheck() {
  setInterval(() => {
    try {
      const textbox = document.querySelector(SMILES_INPUT_SELECTOR);
      if (textbox && textbox.value !== lastTextboxValue) {
        updateJSMEFromTextbox(textbox.value);
      }
    } catch (error) {
      console.error("Error in periodic textbox check:", error);
    }
  }, TEXTBOX_MONITOR_INTERVAL);
}

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Sets a SMILES string in both JSME and Gradio textbox
 * @param {string} smiles - The SMILES string to set
 * @returns {string} The SMILES string that was set
 * @public
 */
window.setJSMESmiles = function (smiles) {
  if (jsmeApplet) {
    updateJSMEFromTextbox(smiles);
  }

  updateGradioTextbox(smiles);
  return smiles;
};

/**
 * Gets the current SMILES string from JSME
 * @returns {string} The current SMILES string, or empty string if unavailable
 * @public
 */
window.getJSMESmiles = function () {
  if (!jsmeApplet) {
    return "";
  }

  try {
    return jsmeApplet.smiles();
  } catch (error) {
    console.error("Error getting SMILES:", error);
    return "";
  }
};

/**
 * Clears both JSME and Gradio textbox
 * @returns {Array} Array containing cleared state for Gradio components
 * @public
 */
window.clearJSME = function () {
  if (jsmeApplet) {
    jsmeApplet.reset();
  }

  updateGradioTextbox("");
  return ["", [], [], "Cleared - Draw a new molecule or enter SMILES"];
};

// ============================================================================
// INITIALIZATION LOGIC
// ============================================================================

/**
 * Checks if JSME library is loaded and initializes when ready
 * Retries until the library becomes available
 */
function initializeWhenReady() {
  if (typeof JSApplet !== "undefined" && JSApplet.JSME) {
    console.log("JSME library loaded, initializing...");
    initializeJSME();
  } else {
    console.log("JSME library not ready, retrying...");
    setTimeout(initializeWhenReady, INIT_RETRY_DELAY);
  }
}

/**
 * Starts the initialization process based on document ready state
 */
function startInitialization() {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      setTimeout(initializeWhenReady, INIT_RETRY_DELAY);
    });
  } else {
    setTimeout(initializeWhenReady, INIT_RETRY_DELAY);
  }
}

// Start the initialization process
startInitialization();
