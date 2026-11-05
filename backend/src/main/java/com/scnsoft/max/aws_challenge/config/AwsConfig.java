package com.scnsoft.max.aws_challenge.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;

/**
 * AWS SDK clients. Credentials come from the default provider chain:
 * the Lambda execution role in AWS, your AWS profile / env vars locally.
 */
@Configuration(proxyBeanMethods = false)
public class AwsConfig {

    @Bean
    BedrockRuntimeClient bedrockRuntimeClient(@Value("${app.aws.region}") String region) {
        return BedrockRuntimeClient.builder()
                .region(Region.of(region))
                .httpClientBuilder(UrlConnectionHttpClient.builder())
                .build();
    }
}
