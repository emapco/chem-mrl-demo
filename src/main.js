/**
 * @fileoverview JSME (JavaScript Molecule Editor) integration with Gradio interface
 * Handles bidirectional synchronization between JSME applet and Gradio textbox
 * @author Manny Cortes ('manny@derifyai.com')
 * @version 0.2.0
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

/** @const {string} Container height for JSME applet */
const CONTAINER_HEIGHT = "450px";

/** @const {string} CSS selector for the Gradio SMILES input element */
const SMILES_INPUT_SELECTOR = "#smiles_input textarea, #smiles_input input";

/** @const {number} Delay for paste event handling (ms) */
const PASTE_DELAY = 50;

/** @const {number} Delay for initialization retry (ms) */
const INIT_RETRY_DELAY = 2000;

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
    // https://jsme-editor.github.io/dist/api_javadoc/index.html
    // http://wiki.jmol.org/index.php/Jmol_JavaScript_Object/JME/Options
    jsmeApplet = new JSApplet.JSME(
      "jsme_container",
      getJsmeContainerWidthPx(),
      CONTAINER_HEIGHT,
      {
        options:
          "rButton,zoom,zoomgui,newLook,star,multipart,polarnitro,NOexportInChI,NOexportInChIkey,NOsearchInChIkey,NOexportSVG,NOpaste",
      }
    );

    jsmeApplet.setCallBack("AfterStructureModified", handleJSMEStructureChange);
    jsmeApplet.setMenuScale(getJsmeGuiScale());
    jsmeApplet.setUserInterfaceBackgroundColor("#adadad");
    jsmeApplet.setMolecularAreaAntiAlias(true);
    jsmeApplet.setMolecularAreaLineWidth(2);
    jsmeApplet.setAtomMolecularAreaFontSize(20);

    // Set initial molecule and sync state
    jsmeApplet.readGenericMolecularInput(DEFAULT_SMILES);
    lastTextboxValue = DEFAULT_SMILES;

    setupTextboxEventListeners();
    window.addEventListener("resize", handleResize);

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

/**
 * Calculates the appropriate GUI scale for the JSME applet based on container width
 * Uses breakpoints to determine optimal scaling for different screen sizes
 * @returns {number} The scale factor for the JSME GUI (0.88 to 2.0)
 */
function getJsmeGuiScale() {
  const width = getJsmeContainerWidthNumber();
  let menuScale;
  if (width > 460) {
    menuScale = 1.3;
  } else if (width > 420) {
    menuScale = 1.1;
  } else if (width > 370) {
    menuScale = 1.05;
  } else if (width > 300) {
    menuScale = 0.88;
  } else {
    menuScale = 2;
  }
  return menuScale;
}

/**
 * Gets the JSME container width as a CSS-compatible string value
 * Returns either a pixel value or percentage based on available width
 * @returns {string} Width as "100%" or "{width}px" format
 */
function getJsmeContainerWidthPx() {
  const parentWidth = getJsmeContainerWidthNumber();
  if (parentWidth == null || parentWidth <= 0) {
    return "100%";
  }
  return `${parentWidth}px`;
}

/**
 * Gets the numeric width of the JSME container's parent element
 * Used for responsive scaling calculations
 * @returns {number|null} Width in pixels, or null if container not found
 */
function getJsmeContainerWidthNumber() {
  const container = document.getElementById("jsme_container");
  if (!container) {
    return null;
  }
  return container.parentNode.offsetWidth;
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
// UI MONITORING
// ============================================================================

/**
 * Finds the textbox element and sets up event listeners
 */
function setupTextboxEventListeners() {
  const textbox = document.querySelector(SMILES_INPUT_SELECTOR);
  if (!textbox) {
    return;
  }

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
 * Handles window resize events and updates JSME applet width
 */
function handleResize() {
  if (!jsmeApplet) {
    return;
  }

  try {
    jsmeApplet.setMenuScale(getJsmeGuiScale());
    jsmeApplet.setWidth(getJsmeContainerWidthPx());
  } catch (error) {
    console.error("Error resizing JSME applet:", error);
  }
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
 * Checks if JSME library is loaded and initializes JSME applet
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

startInitialization();
