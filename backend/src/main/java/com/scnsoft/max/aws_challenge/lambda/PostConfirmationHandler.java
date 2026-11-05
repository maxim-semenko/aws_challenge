package com.scnsoft.max.aws_challenge.lambda;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.CognitoUserPoolPostConfirmationEvent;
import com.scnsoft.max.aws_challenge.AwsChallengeApplication;
import com.scnsoft.max.aws_challenge.user.UserSyncService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

import java.util.Map;

/**
 * "Sync Lambda": Cognito User Pool PostConfirmation trigger that upserts the confirmed user into PostgreSQL.
 * <p>
 * Cognito invokes the Lambda directly (User Pool -> Triggers -> Post confirmation) and expects the
 * event to be returned unchanged. If this handler throws, the user sees an error during sign-up.
 * <p>
 * Lambda handler: {@code com.scnsoft.max.aws_challenge.lambda.PostConfirmationHandler::handleRequest}
 */
public class PostConfirmationHandler
        implements RequestHandler<CognitoUserPoolPostConfirmationEvent, CognitoUserPoolPostConfirmationEvent> {

    private static final Logger log = LoggerFactory.getLogger(PostConfirmationHandler.class);

    // Non-web Spring context, created once per execution environment
    private static final ConfigurableApplicationContext CONTEXT = new SpringApplicationBuilder(AwsChallengeApplication.class)
            .web(WebApplicationType.NONE)
            .profiles("lambda")
            .run();

    private final UserSyncService userSyncService = CONTEXT.getBean(UserSyncService.class);

    @Override
    public CognitoUserPoolPostConfirmationEvent handleRequest(CognitoUserPoolPostConfirmationEvent event, Context context) {
        MDC.put("awsRequestId", context.getAwsRequestId());
        try {
            Map<String, String> attributes = event.getRequest().getUserAttributes();
            String sub = attributes.get("sub");
            String email = attributes.get("email");

            log.info("PostConfirmation trigger: source={}, userPool={}, sub={}", event.getTriggerSource(), event.getUserPoolId(), sub);
            userSyncService.upsert(sub, email, event.getUserName());
            return event;
        } finally {
            MDC.clear();
        }
    }
}
