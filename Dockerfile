# Multi-stage Dockerfile for Iceberg TPC-DS Benchmark
FROM openjdk:11-jdk-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gcc \
    g++ \
    make \
    python3 \
    python3-pip \
    git \
    bison \
    flex \
    byacc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Download Spark
RUN wget https://archive.apache.org/dist/spark/spark-3.4.2/spark-3.4.2-bin-hadoop3.tgz \
    && tar -xzf spark-3.4.2-bin-hadoop3.tgz \
    && mv spark-3.4.2-bin-hadoop3 spark \
    && rm spark-3.4.2-bin-hadoop3.tgz

# Note: TPC-DS data generation is now handled by PySpark (no native binaries needed)

# Download Iceberg jars
RUN mkdir -p /opt/spark/jars/iceberg \
    && cd /opt/spark/jars/iceberg \
    && wget https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.4_2.12/1.5.0/iceberg-spark-runtime-3.4_2.12-1.5.0.jar \
    && wget https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar \
    && wget https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar

# Final stage - smaller runtime image
FROM openjdk:11-jre-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    procps \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /opt/spark /opt/spark

# Set environment variables
ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY src/ /app/src/
COPY configs/ /app/configs/
COPY scripts/ /app/scripts/

# Set working directory
WORKDIR /app

# Create data and output directories
RUN mkdir -p /app/data /app/output /app/metrics

# Set default command
CMD ["python3", "-m", "src.iceberg_benchmark.cli", "--help"]
