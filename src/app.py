import gradio as gr
import numpy as np
import pandas as pd
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

            logger.info(f"Running similarity search: {smiles} - ({embed_dim})")
            embedding = self.embedding_service.get_molecular_embedding(smiles, embed_dim)
            neighbors = self.embedding_service.find_similar_molecules(embedding, embed_dim)

            return embedding.tolist(), neighbors, "Search completed successfully"

        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            logger.error(error_msg)
            return [], [], error_msg

    @staticmethod
    def _truncated_attribute(obj, attr, max_len=45):
        return f"{obj[attr][:max_len]}{'...' if len(obj[attr]) > max_len else ''}"

    @classmethod
    def _draw_molecule_grid(cls, similar: list[SimilarMolecule]) -> np.ndarray:
        mols = [Chem.MolFromSmiles(m["smiles"]) for m in similar]
        legends = [
            f"{cls._truncated_attribute(m, 'name')}\n{m['properties']}\n"
            f"{cls._truncated_attribute(m, 'smiles')}\n{m['score']:.2E}"
            for m in similar
        ]

        draw_options = rdMolDraw2D.MolDrawOptions()
        draw_options.legendFontSize = 17
        draw_options.legendFraction = 0.29
        draw_options.drawMolsSameScale = False

        img = Draw.MolsToGridImage(
            mols,
            legends=legends,
            molsPerRow=3,
            subImgSize=(250, 250),
            drawOptions=draw_options,
        )
        return img

    @staticmethod
    def _display_sample_molecules(mols: pd.DataFrame):
        for _, row in mols.iterrows():
            with gr.Group():
                gr.Textbox(
                    value=row["smiles"], label=f"{row['name']} ({row['properties']})", interactive=False, scale=3
                )
                sample_btn = gr.Button(
                    f"Load {row['name']}",
                    scale=1,
                    size="sm",
                    variant="primary",
                )
                sample_btn.click(
                    fn=None,
                    js=f"() => {{window.setCWSmiles('{row['smiles']}');}}",
                )

    @staticmethod
    def clear_all():
        return "", "", [], [], None, "Cleared - Draw a new molecule or enter SMILES"

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
<link rel="preload" href="gradio_api/file=src/static/chemwriter/chemwriter.css" as="style">
<link rel="preload" href="gradio_api/file=src/static/chemwriter/chemwriter-user.css" as="style">
<link rel="preload" href="gradio_api/file=src/static/chemwriter/chemwriter.js" as="script">
<link rel="preload" href="gradio_api/file=src/static/main.min.js" as="script">
<link rel="stylesheet" href="gradio_api/file=src/static/chemwriter/chemwriter.css">
<link rel="stylesheet" href="gradio_api/file=src/static/chemwriter/chemwriter-user.css">
<script src="gradio_api/file=src/static/chemwriter/chemwriter.js" defer></script>
<script src="gradio_api/file=src/static/main.min.js" defer></script>
        """

        with gr.Blocks(
            title="Chem-MRL: Molecular Similarity Search Demo",
            theme=gr.themes.Soft(),  # type: ignore
            head=head_scripts,
        ) as demo:
            gr.Markdown("""
            # 🧪 Chem-MRL: Molecular Similarity Search Demo

            Use the ChemWriter editor to draw a molecule or input a SMILES string.<br/>
            The backend encodes the molecule using the Chem-MRL model to produce a vector embedding.<br/>
            Similarity search is performed via an HNSW-indexed Redis vector store to retrieve closest matches.
            """)
            gr.HTML(
                """
            The Redis database indexes <a href="https://isomerdesign.com/pihkal/home">Isomer Design's</a> molecular library.
            <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">
                <img src="https://mirrors.creativecommons.org/presskit/buttons/80x15/svg/by-nc-sa.svg" alt="License: CC BY-NC-SA 4.0"
             style="display:inline; height:15px; vertical-align:middle; margin-left:4px;"/>
            </a>""",  # noqa: E501
                padding=False,
            )
            gr.Markdown(
                "[Model Repo](https://github.com/emapco/chem-mrl) | [Demo Repo](https://github.com/emapco/chem-mrl-demo)"
            )
            with gr.Tab("🔬 Molecular Search"), gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Molecule Input")
                    gr.HTML(
                        '<div id="editor" class="chemwriter" '
                        'data-chemwriter-ui="editor" '
                        'data-chemwriter-width="100%" data-chemwriter-height="450"></div>'
                    )

                    smiles_input = gr.Textbox(
                        label="SMILES String",
                        placeholder="Draw a molecule above or enter SMILES here (e.g., CCO for ethanol)",
                        lines=2,
                        elem_id="smiles_input",
                        show_copy_button=True,
                    )

                    mol_input = gr.Textbox(
                        label="Molecule Input",
                        interactive=False,
                        elem_id="mol_input",
                        show_copy_button=True,
                        visible=False,
                    )

                    canonical_smiles_output = gr.Textbox(
                        label="Canonical SMILES",
                        placeholder="Canonical representation will appear here",
                        lines=2,
                        interactive=False,
                        elem_id="canonical_smiles_output",
                        show_copy_button=True,
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
                    gr.Markdown("### Search Results")
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

                    molecule_image = gr.Image(label="Similar Molecules Grid", type="pil")

            with gr.Tab("📊 Sample Molecules"):
                gr.Markdown("""
                Click any button below to load the molecule into the ChemWriter editor:
                """)

                with gr.Row():
                    with gr.Column(scale=1):
                        self._display_sample_molecules(SAMPLE_SMILES[::3])
                    with gr.Column(scale=1):
                        self._display_sample_molecules(SAMPLE_SMILES[1::3])
                    with gr.Column(scale=1):
                        self._display_sample_molecules(SAMPLE_SMILES[2::3])

            # Update canonical SMILES when input changes
            smiles_input.change(
                fn=self.embedding_service.get_canonical_smiles,
                inputs=[smiles_input],
                outputs=[canonical_smiles_output],
                api_name="get_canonical_smiles",
            )

            mol_input.change(
                fn=self.embedding_service.get_smiles_from_mol_file,
                inputs=[mol_input],
                outputs=[smiles_input],
            )

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
                js="window.clearCW",
                outputs=[
                    smiles_input,
                    canonical_smiles_output,
                    embedding_output,
                    similar_molecules_output,
                    molecule_image,
                    status_output,
                ],
            )

            gr.set_static_paths(paths=["src/static"])

        return demo


if __name__ == "__main__":
    app = App()
    app.demo.launch(**LAUNCH_PARAMETERS)
