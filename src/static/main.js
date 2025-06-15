/**
 * @fileoverview ChemWriter integration with Gradio interface
 * Handles bidirectional synchronization between ChemWriter editor and Gradio textbox
 * @author Manny Cortes ('manny@derifyai.com')
 * @version 0.3.0
 */

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

/** @type {Object|null} The ChemWriter editor instance */
let editor = null;
let chemwriter = null;

// ============================================================================
// CONSTANTS
// ============================================================================

/** @const {string} Default SMILES for initial molecule (ethanol) */
const DEFAULT_SMILES = "CN(C)CCC1=CNC2=C1C(=CC=C2)OP(=O)(O)O";

/** @const {string} CSS selector for the Gradio SMILES input element */
const SMILES_INPUT_SELECTOR = "#smiles_input textarea, #smiles_input input";

/** @const {string} CSS selector for the Gradio Mol file input element */
const MOL_INPUT_SELECTOR = "#mol_input textarea, #mol_input input";

/** @const {number} Delay for paste event handling (ms) */
const PASTE_DELAY = 50;

/** @const {number} Delay for initialization retry (ms) */
const INIT_RETRY_DELAY = 250;

/** @const {string[]} Events to trigger for Gradio change detection */
const GRADIO_CHANGE_EVENTS = ["input", "change"];

// ============================================================================
// CORE INITIALIZATION
// ============================================================================

/**
 * Initializes ChemWriter editor and sets up event handlers
 */
function initializeChemWriter() {
  try {
    setupSmilesTextboxEventListeners();
    setupChemWriterEventListeners();
    editor.setSMILES(DEFAULT_SMILES);
    console.log("ChemWriter initialized successfully");
  } catch (error) {
    console.error("Error initializing ChemWriter:", error);
  }
}

// ============================================================================
// GRADIO AND CHEMWRITER INTEGRATION
// ============================================================================

/**
 * Updates the mol_input Gradio textbox with a mol file string
 * Triggers appropriate events to ensure Gradio detects the change
 */
function updateGradioTextbox() {
  try {
    const molTextbox = document.querySelector(MOL_INPUT_SELECTOR);
    const molFile = editor?.getMolfile();
    molTextbox.value = molFile;

    // Trigger events to ensure Gradio detects the change
    GRADIO_CHANGE_EVENTS.forEach((eventType) => {
      const event = new Event(eventType, {
        bubbles: true,
        cancelable: true,
      });
      molTextbox.dispatchEvent(event);
    });
  } catch (error) {
    console.error("Error updating Gradio textbox:", error);
  }
}

/**
 * Updates the ChemWriter editor with a SMILES string from the textbox
 * @param {string} smiles - The SMILES string to display in ChemWriter
 */
function updateChemWriterFromTextbox(smiles) {
  try {
    smiles = smiles.trim();
    editor?.setSMILES(smiles);
  } catch (error) {
    console.error("Error updating ChemWriter from textbox:", error);
  }
}

// ============================================================================
// UI MONITORING
// ============================================================================

function setupSmilesTextboxEventListeners() {
  const textbox = document.querySelector(SMILES_INPUT_SELECTOR);
  if (!textbox) {
    return;
  }
  textbox.addEventListener("input", handleTextboxChange);
  textbox.addEventListener("change", handleTextboxChange);
  textbox.addEventListener("paste", handleTextboxPaste);
}

function setupChemWriterEventListeners() {
  window.addEventListener("resize", () => editor.jd());
  editor.addEventListener('document-edited', updateGradioTextbox);
}

/**
 * Handles textbox change events
 * @param {Event} event - The change event
 */
function handleTextboxChange(event) {
  updateChemWriterFromTextbox(event.target.value);
}

/**
 * Handles textbox paste events with a delay to ensure content is available
 * @param {Event} event - The paste event
 */
function handleTextboxPaste(event) {
  setTimeout(() => {
    updateChemWriterFromTextbox(event.target.value);
  }, PASTE_DELAY);
}

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Sets ChemWriter SMILES string
 * @param {string} smiles - The SMILES string to set
 * @public
 */
window.setCWSmiles = function (smiles) {
  updateChemWriterFromTextbox(smiles);
};

/**
 * Clears both ChemWriter and Gradio textbox
 * @public
 */
window.clearCW = function () {
  editor.setMolfile('\nCWRITER06142521562D\nCreated with ChemWriter - https://chemwriter.com\n  0  0  0  0  0  0  0  0  0  0999 V2000\nM  END');
};

// ============================================================================
// INITIALIZATION LOGIC
// ============================================================================

/**
 * Checks if ChemWriter library is loaded and initializes ChemWriter editor
 */
function initializeWhenReady() {
  chemwriter = window?.chemwriter;
  // The ChemWriter library normally sets up a window load event listener: window.addEventListener("load", function(){Z.De()}, false)
  // However, due to race conditions, the "load" event listener may not be added or triggered in time for proper initialization.
  // So we call the initialization function directly here.
  chemwriter?.System?.De();
  editor = chemwriter?.components?.editor;
  if (typeof chemwriter?.System?.De !== "undefined" && typeof editor !== "undefined") {
    console.log("ChemWriter library loaded, initializing...");
    chemwriter.System.ready(initializeChemWriter);
  } else {
    console.log("ChemWriter library not ready, retrying...");
    setTimeout(initializeWhenReady, INIT_RETRY_DELAY);
  }
}

initializeWhenReady();
