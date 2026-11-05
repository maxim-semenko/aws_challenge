package com.scnsoft.max.aws_challenge.ai;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelResponse;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

/** Text -> vector via Amazon Titan Text Embeddings (Bedrock InvokeModel). */
@Slf4j
@Service
@RequiredArgsConstructor
public class EmbeddingService {

    private final BedrockRuntimeClient bedrock;
    private final BedrockProperties properties;
    private final JsonMapper jsonMapper;

    public float[] embed(String text) {
        ObjectNode request = jsonMapper.createObjectNode()
                .put("inputText", text)
                .put("dimensions", properties.embeddingDimensions())
                .put("normalize", true);   // unit vectors -> cosine distance works well

        long start = System.nanoTime();
        InvokeModelResponse response = bedrock.invokeModel(r -> r
                .modelId(properties.embeddingModelId())
                .contentType("application/json")
                .accept("application/json")
                .body(SdkBytes.fromUtf8String(jsonMapper.writeValueAsString(request))));
        long tookMs = (System.nanoTime() - start) / 1_000_000;

        JsonNode json = jsonMapper.readTree(response.body().asUtf8String());
        JsonNode values = json.get("embedding");
        float[] vector = new float[values.size()];
        for (int i = 0; i < vector.length; i++) {
            vector[i] = values.get(i).floatValue();
        }

        log.info("Bedrock embedding: model={}, inputChars={}, inputTokens={}, dims={}, tookMs={}",
                properties.embeddingModelId(), text.length(), json.path("inputTextTokenCount").asInt(), vector.length, tookMs);
        return vector;
    }
}
