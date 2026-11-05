package com.scnsoft.max.aws_challenge.web;

import com.scnsoft.max.aws_challenge.ai.EmbeddingService;
import com.scnsoft.max.aws_challenge.document.DocumentRepository;
import com.scnsoft.max.aws_challenge.document.DocumentSearchResult;
import com.scnsoft.max.aws_challenge.security.CurrentUserResolver;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** Chatbot Lambda routes: /api/chat/** */
@Slf4j
@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final CurrentUserResolver currentUserResolver;
    private final EmbeddingService embeddingService;
    private final DocumentRepository documentRepository;

    public record SearchRequest(@NotBlank String query, @Min(1) @Max(50) Integer limit) {
    }

    /** Semantic search: question -> Titan embedding -> pgvector k-NN. */
    @PostMapping("/search")
    public List<DocumentSearchResult> search(@Valid @RequestBody SearchRequest body, HttpServletRequest request) {
        currentUserResolver.require(request);
        int limit = body.limit() != null ? body.limit() : 5;

        float[] vector = embeddingService.embed(body.query());
        List<DocumentSearchResult> results = documentRepository.findNearest(DocumentRepository.toVectorLiteral(vector), limit);

        log.info("Vector search: limit={}, results={}", limit, results.size());
        return results;
    }
}
