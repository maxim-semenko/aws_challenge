package com.scnsoft.max.aws_challenge.web;

import com.scnsoft.max.aws_challenge.security.CurrentUser;
import com.scnsoft.max.aws_challenge.security.CurrentUserResolver;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class ApiController {

    private final CurrentUserResolver currentUserResolver;

    /** Public route (no authorizer in API Gateway) - smoke test of the Lambda + API Gateway wiring. */
    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }

    /** Protected route - echoes the claims from the Cognito JWT. */
    @GetMapping("/me")
    public CurrentUser me(HttpServletRequest request) {
        return currentUserResolver.require(request);
    }
}
