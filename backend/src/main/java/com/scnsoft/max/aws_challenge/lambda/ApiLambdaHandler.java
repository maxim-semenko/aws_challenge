package com.scnsoft.max.aws_challenge.lambda;

import com.amazonaws.serverless.exceptions.ContainerInitializationException;
import com.amazonaws.serverless.proxy.model.AwsProxyResponse;
import com.amazonaws.serverless.proxy.model.HttpApiV2ProxyRequest;
import com.amazonaws.serverless.proxy.spring.SpringBootLambdaContainerHandler;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestStreamHandler;
import com.scnsoft.max.aws_challenge.AwsChallengeApplication;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Lambda entry point for API Gateway HTTP API (payload format 2.0).
 * <p>
 * The same deployment package backs both the Chatbot and the Admin Lambda; API Gateway routes
 * {@code /api/chat/**} and {@code /api/admin/**} to the respective function, and Spring MVC
 * dispatches the request to the matching controller.
 * <p>
 * Lambda handler: {@code com.scnsoft.max.aws_challenge.lambda.ApiLambdaHandler::handleRequest}
 */
public class ApiLambdaHandler implements RequestStreamHandler {

    private static final SpringBootLambdaContainerHandler<HttpApiV2ProxyRequest, AwsProxyResponse> HANDLER;

    static {
        try {
            // Spring context is created once per execution environment (cold start) and reused.
            HANDLER = SpringBootLambdaContainerHandler.getHttpApiV2ProxyHandler(AwsChallengeApplication.class, "lambda");
        } catch (ContainerInitializationException e) {
            // Fail the init phase so Lambda starts a fresh environment instead of serving a broken one
            throw new RuntimeException("Could not initialize Spring Boot application", e);
        }
    }

    @Override
    public void handleRequest(InputStream input, OutputStream output, Context context) throws IOException {
        HANDLER.proxyStream(input, output, context);
    }
}
