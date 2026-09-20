import { Module } from '@nestjs/common';
import { ThrottlerModule } from '@nestjs/throttler';
import { APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { AppThrottlerGuard } from './common/guards/app-throttler.guard';
import { LoggingInterceptor } from './common/interceptors/logging.interceptor';
import { AppConfigModule } from './config/app-config.module';
import { PrismaModule } from './database/prisma.module';
import { RedisModule } from './redis/redis.module';
import { HealthModule } from './health/health.module';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { JobsModule } from './jobs/jobs.module';
import { SearchesModule } from './searches/searches.module';
import { NotificationsModule } from './notifications/notifications.module';
import { DashboardModule } from './dashboard/dashboard.module';
import { ExtractorModule } from './extractor/extractor.module';
import { QueuesModule } from './queues/queues.module';
import { QueueServicesModule } from './queues/queue-services.module';

@Module({
  imports: [
    AppConfigModule,
    ThrottlerModule.forRoot({
      throttlers: [{ ttl: 60_000, limit: 100 }],
    }),
    PrismaModule,
    RedisModule,
    QueuesModule,
    QueueServicesModule,
    HealthModule,
    AuthModule,
    UsersModule,
    JobsModule,
    SearchesModule,
    NotificationsModule,
    DashboardModule,
    ExtractorModule,
  ],
  providers: [
    {
      provide: APP_GUARD,
      useClass: AppThrottlerGuard,
    },
    {
      provide: APP_INTERCEPTOR,
      useClass: LoggingInterceptor,
    },
  ],
})
export class AppModule {}
