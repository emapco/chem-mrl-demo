import gradio as gr
import numpy as np
import pandas as pd
from chem_mrl.molecular_fingerprinter import MorganFingerprinter
from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem.Draw import rdMolDraw2D

from constants import EMBEDDING_DIMENSION, LAUNCH_PARAMETERS, SUPPORTED_EMBEDDING_DIMENSIONS
from data import SAMPLE_SMILES
from service import MolecularEmbeddingService, SimilarMolecule, setup_logger

logger = setup_logger()


class App:
    def __init__(self):
        self.embedding_service = MolecularEmbeddingService()
        self.demo = self.create_gradio_interface()

    def molecule_similarity_search_pipeline(
        self, smiles: str, embed_dim: int
    ) -> tuple[list[float], list[SimilarMolecule], str]:
        """Complete pipeline: SMILES -> Canonical SMILES -> Embedding -> Similar molecules"""
        try:
            if not smiles or smiles.strip() == "":
                return [], [], "Please provide a valid SMILES string"

            # Preprocess smiles similarly as training data for optimal performance
            smiles = MorganFingerprinter.canonicalize_smiles(smiles) or smiles

            logger.info(f"Running similarity search for SMILES: {smiles} - dim: {embed_dim}")
            embedding = self.embedding_service.get_molecular_embedding(smiles, embed_dim)
            neighbors = self.embedding_service.find_similar_molecules(embedding, embed_dim)

            return embedding.tolist(), neighbors, "Analysis completed successfully"

        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(error_msg)
            return [], [], error_msg

    @staticmethod
    def _truncated_attribute(obj, attr, max_len=45):
        return f"{obj[attr][:max_len]}{'...' if len(obj[attr]) > max_len else ''}"

    @classmethod
    def _draw_molecule_grid(cls, similar: list[SimilarMolecule]) -> np.ndarray:
        mols = [Chem.MolFromSmiles(m["smiles"]) for m in similar]
        legends = [
            f"{cls._truncated_attribute(m, 'name')}\n{m['category']}\n"
            f"{cls._truncated_attribute(m, 'smiles')}\n({m['score']:.2E})"
            for m in similar
        ]

        draw_options = rdMolDraw2D.MolDrawOptions()
        draw_options.legendFontSize = 17
        draw_options.legendFraction = 0.29
        draw_options.drawMolsSameScale = False

        img = Draw.MolsToGridImage(
            mols,
            legends=legends,
            molsPerRow=2,
            subImgSize=(250, 250),
            drawOptions=draw_options,
        )
        return img

    @staticmethod
    def _display_sample_molecules(mols: pd.DataFrame):
        for _, row in mols.iterrows():
            with gr.Group():
                gr.Textbox(value=row["smiles"], label=f"{row['name']} ({row['category']})", interactive=False, scale=3)
                sample_btn = gr.Button(
                    f"Load {row['name']}",
                    scale=1,
                    size="sm",
                    variant="primary",
                )
                sample_btn.click(
                    fn=None,
                    js=f"() => {{window.setJSMESmiles('{row['smiles']}');}}",
                )

    @staticmethod
    def clear_all():
        return "", [], [], None, "Cleared - Draw a new molecule or enter SMILES"

    def handle_search(self, smiles: str, embed_dim: int):
        if not smiles.strip():
            return (
                [],
                [],
                None,
                "Please draw a molecule or enter a SMILES string",
            )
        embedding, similar, status = self.molecule_similarity_search_pipeline(smiles, embed_dim)
        img = self._draw_molecule_grid(similar)
        return embedding, similar, img, status

    def create_gradio_interface(self):
        """Create the Gradio interface optimized for JavaScript client usage"""
        head_scripts = """
<link rel="preconnect" href="https://jsme-editor.github.io">
<link rel="preload" href="https://jsme-editor.github.io/dist/jsme/jsme.nocache.js" as="script" crossorigin="anonymous">
<link rel="preload" href="gradio_api/file=src/main.min.js" as="script">
<script type="text/javascript" src="https://jsme-editor.github.io/dist/jsme/jsme.nocache.js" crossorigin="anonymous" defer></script>
<script type="text/javascript" src="gradio_api/file=src/main.min.js" defer></script>
        """

        with gr.Blocks(
            title="Chem-MRL: Molecular Similarity Search Demo",
            theme=gr.themes.Soft(),
            head=head_scripts,
        ) as demo:
            gr.Markdown("""
            # 🧪 Chem-MRL: Molecular Similarity Search Demo

            Use the JSME editor to draw a molecule or input a SMILES string.
            The backend encodes the molecule using the Chem-MRL model to produce a vector embedding.
            Similarity search is performed via an HNSW-indexed Redis vector store to retrieve closest matches.<br/>

            [Model Repo](https://github.com/emapco/chem-mrl) | [Demo Repo](https://github.com/emapco/chem-mrl-demo)
            """)
            with gr.Tab("🔬 Molecule Analysis"), gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Molecule Input")
                    gr.HTML("<div id='jsme_container'></div>")

                    smiles_input = gr.Textbox(
                        label="SMILES String",
                        placeholder="Draw a molecule above or enter SMILES here (e.g., CCO for ethanol)",
                        lines=2,
                        elem_id="smiles_input",
                    )

                    embedding_dimension = gr.Dropdown(
                        choices=SUPPORTED_EMBEDDING_DIMENSIONS,
                        value=EMBEDDING_DIMENSION,
                        label="Embedding Dimension",
                        elem_id="embedding_dimension",
                    )

                    with gr.Row():
                        search_btn = gr.Button(
                            "🔍 Search Molecule Database",
                            variant="primary",
                            elem_id="search_btn",
                        )
                        clear_btn = gr.Button("🗑️ Clear All", variant="secondary")

                with gr.Column(scale=1):
                    gr.Markdown("### Analysis Results")
                    status_output = gr.Textbox(
                        label="Status",
                        interactive=False,
                        elem_id="status_output",
                        value="Ready - Draw a molecule or enter SMILES",
                    )

                    with gr.Accordion("Molecular Embedding Vector", open=False):
                        embedding_output = gr.JSON(
                            label="Molecular Embedding",
                            elem_id="embedding_output",
                        )

                    with gr.Accordion("Similar Molecules Response", open=False):
                        similar_molecules_output = gr.JSON(
                            label="API Response",
                            elem_id="similar_molecules_output",
                        )

                    molecule_image = gr.Image(label="Similiar Molecules Grid", type="pil")

            with gr.Tab("📊 Sample Molecules"):
                gr.Markdown("""
                ### Sample Molecules in Database
                Click any button below to load the molecule into the JSME editor:
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        self._display_sample_molecules(SAMPLE_SMILES[::3])
                    with gr.Column(scale=1):
                        self._display_sample_molecules(SAMPLE_SMILES[1::3])
                    with gr.Column(scale=1):
                        self._display_sample_molecules(SAMPLE_SMILES[2::3])

            # Main analysis
            search_btn.click(
                fn=self.handle_search,
                inputs=[smiles_input, embedding_dimension],
                outputs=[
                    embedding_output,
                    similar_molecules_output,
                    molecule_image,
                    status_output,
                ],
                api_name="molecule_similarity_search_pipeline",
            )

            # Clear UI state
            clear_btn.click(
                fn=self.clear_all,
                js="window.clearJSME",
                outputs=[
                    smiles_input,
                    embedding_output,
                    similar_molecules_output,
                    molecule_image,
                    status_output,
                ],
            )

            gr.set_static_paths(paths=["src/"])

        return demo


if __name__ == "__main__":
    app = App()
    app.demo.launch(**LAUNCH_PARAMETERS)
