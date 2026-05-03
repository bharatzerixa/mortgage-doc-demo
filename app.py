import streamlit as st

from models.loan_file import LoanFile
from services.stip_generator import StipListGenerator
from services.classifier import DocumentClassifier
from services.paystub_extractor import PayStubExtractor
from services.generic_extractor import GenericExtractor
from ui.sidebar import Sidebar
from ui.intake import IntakeView
from ui.documents import DocumentsView
from ui.review import ReviewView


st.set_page_config(page_title="BHS Mortgage Workflow", layout="wide")


# --- Session state ---
def get_loan_file() -> LoanFile:
    if "loan_file" not in st.session_state:
        st.session_state.loan_file = LoanFile()
    return st.session_state.loan_file


def reset_loan_file():
    st.session_state.loan_file = LoanFile()


# --- Service container (built once per session) ---
def get_services():
    if "services" not in st.session_state:
        st.session_state.services = {
            "stip_generator": StipListGenerator(),
            "classifier": DocumentClassifier(),
            "paystub_extractor": PayStubExtractor(),
            "generic_extractor": GenericExtractor(),
        }
    return st.session_state.services


# --- Router ---
def main():
    lf = get_loan_file()
    services = get_services()

    Sidebar(lf, on_reset=reset_loan_file).render()

    if lf.stage == "intake":
        IntakeView(lf, services["stip_generator"]).render()
    elif lf.stage == "documents":
        DocumentsView(
            lf,
            classifier=services["classifier"],
            paystub_extractor=services["paystub_extractor"],
            generic_extractor=services["generic_extractor"],
        ).render()
    elif lf.stage == "review":
        ReviewView(lf).render()
    else:
        st.title(f"Workflow stage: {lf.stage}")
        st.info("Coming next.")


main()