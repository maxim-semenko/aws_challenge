package com.scnsoft.max.aws_challenge.web;

import com.amazonaws.serverless.proxy.RequestReader;
import com.amazonaws.serverless.proxy.model.HttpApiV2ProxyRequestContext;
import com.amazonaws.services.lambda.runtime.Context;
import com.scnsoft.max.aws_challenge.security.CurrentUserResolver;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Puts correlation ids into the MDC so every JSON log line of a request carries them
 * (API Gateway requestId -> Lambda awsRequestId -> user sub), then logs one access line per request.
 */
@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
@RequiredArgsConstructor
public class RequestLoggingFilter extends OncePerRequestFilter {

    private final CurrentUserResolver currentUserResolver;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        long start = System.nanoTime();
        try {
            if (request.getAttribute(RequestReader.LAMBDA_CONTEXT_PROPERTY) instanceof Context lambda) {
                MDC.put("awsRequestId", lambda.getAwsRequestId());
            }
            if (request.getAttribute(RequestReader.HTTP_API_CONTEXT_PROPERTY) instanceof HttpApiV2ProxyRequestContext api) {
                MDC.put("apiRequestId", api.getRequestId());
            }
            currentUserResolver.resolve(request).ifPresent(u -> MDC.put("userSub", u.sub()));

            chain.doFilter(request, response);
        } finally {
            log.info("{} {} -> {} in {} ms", request.getMethod(), request.getRequestURI(), response.getStatus(),
                    (System.nanoTime() - start) / 1_000_000);
            MDC.clear();
        }
    }
}
