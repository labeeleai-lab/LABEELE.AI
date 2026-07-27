# Use Python 3.10
FROM python:3.10

# Set working directory
WORKDIR /app

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup User (Hugging Face Requirement)
RUN useradd -m -u 1000 user

# 3. Install Python Packages (before switching to user)
COPY --chown=user requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir --upgrade -r requirements.txt

# 4. Copy the Application Code
COPY --chown=user . .

# 5. Create Storage Directories (while still root, then change ownership)
RUN mkdir -p data labeele_duke/fine_tuned_weights labeele_duke/duke_chat_brain duke_checkpoints && \
    chown -R user:user /app

# 6. Switch to non-root user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# 7. Expose the Port (must match app_port in README.md's HF Space config)
EXPOSE 7860

# 8. Start the API
CMD ["uvicorn", "coordinator_api:app", "--host", "0.0.0.0", "--port", "7860"]