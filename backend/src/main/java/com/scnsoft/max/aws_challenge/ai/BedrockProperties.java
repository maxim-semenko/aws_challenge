package com.scnsoft.max.aws_challenge.ai;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * @param embeddingModelId    e.g. amazon.titan-embed-text-v2:0 (model access must be enabled in the Bedrock console)
 * @param embeddingDimensions 256, 512 or 1024 for Titan v2; must match the vector(n) column
 */
@ConfigurationProperties(prefix = "app.bedrock")
public record BedrockProperties(String embeddingModelId, int embeddingDimensions) {
}
