import streamlit as st

from models.loan_file import LoanFile
from services.stip_generator import StipListGenerator
from services.classifier import DocumentClassifier
from services.paystub_extractor import PayStubExtractor
from services.generic_extractor import GenericExtractor
from services.followup_generator import FollowupGenerator
from services.scrubber import PreSubmissionScrubber
from services.inbox_seeder import InboxSeeder
from services.borrower_validator import BorrowerValidator
from ui.sidebar import Sidebar
from ui.borrower import BorrowerView
from ui.intake import IntakeView
from ui.documents import DocumentsView
from ui.review import ReviewView
from ui.followup import FollowupView
from ui.scrub import ScrubView
from ui.done import DoneView


st.set_page_config(page_title="BHS Mortgage Workflow", layout="wide")


# --- Session state ---
def get_loan_file() -> LoanFile:
    if "loan_file" not in st.session_state:
        st.session_state.loan_file = LoanFile()
    return st.session_state.loan_file


def reset_loan_file():
    st.session_state.loan_file = LoanFile()
    st.session_state["inbox_seeded"] = False
    st.session_state["borrower_stage"] = "intake"
    st.session_state["active_view"] = "processor"
    # Clear processed files tracking on reset
    if "processed_files" in st.session_state:
        del st.session_state["processed_files"]


# --- Service container (built once per session) ---
def get_services():
    if "services" not in st.session_state:
        classifier = DocumentClassifier()
        paystub_extractor = PayStubExtractor()
        generic_extractor = GenericExtractor()

        st.session_state.services = {
            "stip_generator": StipListGenerator(),
            "classifier": classifier,
            "paystub_extractor": paystub_extractor,
            "generic_extractor": generic_extractor,
            "followup_generator": FollowupGenerator(),
            "scrubber": PreSubmissionScrubber(),
            "borrower_validator": BorrowerValidator(classifier, paystub_extractor, generic_extractor),
        }
    return st.session_state.services


# --- Router ---
def main():
    lf = get_loan_file()
    services = get_services()

    # Seed inbox when entering documents stage for the first time
    if lf.stage == "documents" and not lf.pending_docs and not st.session_state.get("inbox_seeded"):
        seeder = InboxSeeder()
        seeder.seed(lf)
        st.session_state["inbox_seeded"] = True

    Sidebar(lf, on_reset=reset_loan_file).render()

    # Get active view
    active_view = st.session_state.get("active_view", "processor")

    # Route based on active view
    if active_view == "borrower":
        BorrowerView(
            lf,
            stip_generator=services["stip_generator"],
            validator=services["borrower_validator"],
        ).render()
        return

    # Processor view (original workflow)
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
    elif lf.stage == "followup":
        FollowupView(lf, services["followup_generator"]).render()
    elif lf.stage == "scrub":
        ScrubView(lf, services["scrubber"]).render()
    elif lf.stage == "done":
        DoneView(lf).render()
    else:
        st.title(f"Workflow stage: {lf.stage}")
        st.info("Coming next.")


main()