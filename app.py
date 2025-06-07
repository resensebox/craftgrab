# this_day_in_history_app.py

import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
from openai import OpenAI

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="This Day in History", layout="centered")

# --- Custom CSS ---
st.markdown("""
<style>
body { background-color: #e8f0fe; font-family: 'Inter', sans-serif; }
h1 { text-align: center; color: #333333; margin: 2rem auto 1.5rem; font-size: 2.5em; font-weight: 700; }
.stButton>button { background-color: #4CAF50; color: white; padding: 0.8em 2em; border: none; border-radius: 8px; font-weight: bold; box-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
.stButton>button:hover { background-color: #45a049; transform: translateY(-2px); }
.stTextInput>div>div>input { border-radius: 8px; padding: 10px; border: 1px solid #ccc; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); }
.stTextInput>div>div>input:focus { border-color: #4CAF50; }
.stAlert { border-radius: 8px; background-color: #e6f7ff; border-color: #91d5ff; color: #004085; }
</style>
""", unsafe_allow_html=True)

# --- OpenAI Init ---
try:
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("❌ OPENAI_API_KEY is missing from secrets. Please add it to your Streamlit secrets.")
        st.stop()
    client_ai = OpenAI(api_key=st.secrets["OPEN_AI_KEY"])
except Exception as e:
    st.error(f"Failed to initialize OpenAI. Error: {e}")
    st.stop()

# --- PDF helpers ---
def generate_article_pdf(title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, title, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, content.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

def generate_full_history_pdf(event_title, event_article, born_section, fun_fact_section, trivia_section, today_str, name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.multi_cell(0, 10, f"This Day in History: {today_str}", align='C')
    pdf.ln(10)

    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Significant Event:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, f"**{event_title}**\n{event_article}".encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Famous Person Born Today:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, born_section.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Fun Fact:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, fun_fact_section.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Trivia Time! (with answers for the volunteer):")
    pdf.set_font("Arial", "", 12)
    for t in trivia_section:
        pdf.multi_cell(0, 8, t.encode('latin-1', 'replace').decode('latin-1'))

    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 5, f"Generated for {name} by Mindful Libraries on {today_str}".encode('latin-1', 'replace').decode('latin-1'), align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- AI fetch ---
@st.cache_data(ttl=86400)
def get_this_day_in_history(day, month, profile, _client):
    profile_str = ", ".join([f"{k}: {v}" for k, v in profile.items() if v])
    prompt = f"""
    You are a historical assistant. Provide:
    1. A positive/cultural event from {month:02d}-{day:02d} (1900-1965)
    2. A famous birth (1850-1960) relevant to: {profile_str}
    3. A fun fact for this date
    4. 3 trivia questions and answers, easy to recognize
    Format:
    Event: [Title] - [Year]\n[200 words]
    Born on this Day: [Name]\n[Description]
    Fun Fact: [Fact]
    Trivia Questions:\n1. Q? (Answer: A)\n...
    """
    try:
        res = _client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR: {e}"

# --- Main App ---
st.header("🗓️ This Day in History!")

name = st.text_input("Enter Pair's Name:", "")
today = st.date_input("Select a date", value=date.today(), max_value=date.today())

day, month = today.day, today.month
today_str = today.strftime('%B %d, %Y')
profile = {"name": name, "jobs": "", "hobbies": "", "decade": "", "life_experiences": ""}

if name:
    if 'last_date' not in st.session_state or st.session_state['last_date'] != today:
        with st.spinner("Getting today's facts..."):
            raw = get_this_day_in_history(day, month, profile, client_ai)
            if raw.startswith("ERROR"):
                st.error(raw)
                st.stop()

            sections = raw.split("\n\n")
            parsed = {"event_title": "", "event_article": "", "born_section": "", "fun_fact": "", "trivia": []}
            for section in sections:
                if section.startswith("Event:"):
                    first = section.split("\n")[0].replace("Event:", "").strip()
                    if ' - ' in first:
                        parsed["event_title"] = first.split(' - ')[0].strip()
                    parsed["event_article"] = "\n".join(section.split("\n")[1:])
                elif section.startswith("Born on this Day:"):
                    parsed["born_section"] = section.replace("Born on this Day:", "").strip()
                elif section.startswith("Fun Fact:"):
                    parsed["fun_fact"] = section.replace("Fun Fact:", "").strip()
                elif section.startswith("Trivia Questions:"):
                    lines = section.replace("Trivia Questions:", "").strip().split("\n")
                    parsed["trivia"] = [line.strip() for line in lines if line.strip()]

            st.session_state['parsed'] = parsed
            st.session_state['last_date'] = today

    parsed = st.session_state['parsed']

    st.markdown(f"### Today is: {today_str}")
    st.subheader("Significant Event:")
    st.markdown(f"**{parsed['event_title']}**")
    st.info(parsed['event_article'])
    st.download_button("Download Article PDF", generate_article_pdf(parsed['event_title'], parsed['event_article']), file_name=f"{parsed['event_title'].replace(' ', '_')}.pdf")

    st.markdown("---")
    st.subheader("Famous Person Born Today:")
    name_guess = parsed['born_section'].split('\n')[0] if '\n' in parsed['born_section'] else parsed['born_section']
    st.image(f"https://placehold.co/150x150?text={name_guess}", width=150)
    st.markdown(parsed['born_section'])

    st.markdown("---")
    st.subheader("Fun Fact:")
    st.info(parsed['fun_fact'])

    st.markdown("---")
    st.subheader("Trivia Time!")
    for t in parsed['trivia']:
        st.markdown(t)

    st.markdown("---")
    st.subheader("Full Summary PDF")
    full_pdf = generate_full_history_pdf(parsed['event_title'], parsed['event_article'], parsed['born_section'], parsed['fun_fact'], parsed['trivia'], today_str, name)
    st.download_button("Download Full PDF", full_pdf, file_name=f"This_Day_{today.strftime('%Y_%m_%d')}.pdf")
else:
    st.info("Enter a Pair's Name to begin")

