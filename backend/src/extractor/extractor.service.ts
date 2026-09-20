import {
  HttpException,
  Injectable,
  Logger,
  ServiceUnavailableException,
} from '@nestjs/common';
import { AppConfigService } from '../config/app-config.service';
import { WarehouseFiltersDto } from '../searches/dto/warehouse-filters.dto';

const REQUEST_TIMEOUT_MS = 10_000;

@Injectable()
export class ExtractorService {
  private readonly logger = new Logger(ExtractorService.name);

  constructor(private readonly config: AppConfigService) {}

  startRun(filters: WarehouseFiltersDto) {
    return this.requestJson('/runs', {
      method: 'POST',
      body: JSON.stringify({ ...filters, schedule: filters.schedule ?? [] }),
    });
  }

  currentRun() {
    return this.requestJson('/runs/current');
  }

  getRun(id: string) {
    return this.requestJson(`/runs/${encodeURIComponent(id)}`);
  }

  async getFrame(id: string): Promise<Buffer> {
    const response = await this.request(`/runs/${encodeURIComponent(id)}/frame`);
    return Buffer.from(await response.arrayBuffer());
  }

  private async requestJson(path: string, init: RequestInit = {}): Promise<unknown> {
    const response = await this.request(path, init);
    return response.json();
  }

  private async request(path: string, init: RequestInit = {}): Promise<Response> {
    const baseUrl = this.config.warehouseExtractorUrl;
    if (!baseUrl) {
      throw new ServiceUnavailableException('WAREHOUSE_EXTRACTOR_URL não configurada');
    }

    let response: Response;
    try {
      response = await fetch(`${baseUrl.replace(/\/$/, '')}${path}`, {
        ...init,
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      });
    } catch (error) {
      this.logger.warn(`Extrator inacessível em ${baseUrl}: ${(error as Error).message}`);
      throw new ServiceUnavailableException('Extrator indisponível');
    }

    if (!response.ok) {
      let message = `Extrator respondeu ${response.status}`;
      try {
        const body = (await response.json()) as { detail?: unknown };
        if (typeof body.detail === 'string') message = body.detail;
      } catch {
        // resposta sem JSON: mantém a mensagem padrão
      }
      throw new HttpException(message, response.status);
    }
    return response;
  }
}
